"""
ComfyUI client for interfacing with ComfyUI API
"""
import httpx
import json
import asyncio
import uuid
from typing import Dict, Any, Optional, List
import os
import logging

logger = logging.getLogger(__name__)

class ComfyUIClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.getenv("COMFYUI_BASE_URL", "http://comfyui:8188")
        self.base_url = self.base_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=60.0)
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if ComfyUI is available and responsive"""
        try:
            response = await self.client.get(f"{self.base_url}/system_stats")
            response.raise_for_status()
            return {
                "status": "healthy",
                "response_time": response.elapsed.total_seconds(),
                "system_stats": response.json()
            }
        except Exception as e:
            logger.error(f"ComfyUI health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def get_models(self) -> Dict[str, List[str]]:
        """Get available models from ComfyUI"""
        try:
            response = await self.client.get(f"{self.base_url}/object_info")
            response.raise_for_status()
            object_info = response.json()
            
            models = {}
            
            # Extract checkpoint models
            if "CheckpointLoaderSimple" in object_info:
                checkpoint_info = object_info["CheckpointLoaderSimple"]["input"]["required"]
                if "ckpt_name" in checkpoint_info:
                    models["checkpoints"] = checkpoint_info["ckpt_name"][0]
            
            # Extract VAE models
            if "VAELoader" in object_info:
                vae_info = object_info["VAELoader"]["input"]["required"]
                if "vae_name" in vae_info:
                    models["vae"] = vae_info["vae_name"][0]
            
            # Extract ControlNet models
            if "ControlNetLoader" in object_info:
                controlnet_info = object_info["ControlNetLoader"]["input"]["required"]
                if "control_net_name" in controlnet_info:
                    models["controlnet"] = controlnet_info["control_net_name"][0]
            
            # Extract LoRA models
            if "LoraLoader" in object_info:
                lora_info = object_info["LoraLoader"]["input"]["required"]
                if "lora_name" in lora_info:
                    models["lora"] = lora_info["lora_name"][0]
            
            return models
            
        except Exception as e:
            logger.error(f"Failed to get models from ComfyUI: {str(e)}")
            return {}
    
    async def queue_prompt(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """Queue a workflow for execution"""
        try:
            # Generate a unique client_id for this request
            client_id = str(uuid.uuid4())
            
            prompt_data = {
                "prompt": workflow,
                "client_id": client_id
            }
            
            response = await self.client.post(
                f"{self.base_url}/prompt",
                json=prompt_data
            )
            response.raise_for_status()
            result = response.json()
            
            return {
                "success": True,
                "prompt_id": result.get("prompt_id"),
                "client_id": client_id,
                "number": result.get("number")
            }
            
        except Exception as e:
            logger.error(f"Failed to queue prompt: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_history(self, prompt_id: Optional[str] = None) -> Dict[str, Any]:
        """Get execution history"""
        try:
            url = f"{self.base_url}/history"
            if prompt_id:
                url += f"/{prompt_id}"
            
            response = await self.client.get(url)
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Failed to get history: {str(e)}")
            return {}
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        try:
            response = await self.client.get(f"{self.base_url}/queue")
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Failed to get queue status: {str(e)}")
            return {}
    
    async def cancel_prompt(self, prompt_id: str) -> bool:
        """Cancel a queued prompt"""
        try:
            response = await self.client.post(
                f"{self.base_url}/interrupt",
                json={"delete": [prompt_id]}
            )
            response.raise_for_status()
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel prompt {prompt_id}: {str(e)}")
            return False
    
    async def generate_simple_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 512,
        height: int = 512,
        steps: int = 20,
        cfg: float = 7.0,
        seed: Optional[int] = None,
        checkpoint: str = "sd_v1-5_pruned_emaonly.safetensors"
    ) -> Dict[str, Any]:
        """Generate an image using a simple text-to-image workflow"""
        
        # Generate random seed if not provided
        if seed is None:
            seed = int.from_bytes(os.urandom(4), byteorder='big') % (2**32)
        
        # Create a simple workflow
        workflow = {
            "1": {
                "inputs": {
                    "ckpt_name": checkpoint
                },
                "class_type": "CheckpointLoaderSimple"
            },
            "2": {
                "inputs": {
                    "text": prompt,
                    "clip": ["1", 1]
                },
                "class_type": "CLIPTextEncode"
            },
            "3": {
                "inputs": {
                    "text": negative_prompt,
                    "clip": ["1", 1]
                },
                "class_type": "CLIPTextEncode"
            },
            "4": {
                "inputs": {
                    "seed": seed,
                    "steps": steps,
                    "cfg": cfg,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["1", 0],
                    "positive": ["2", 0],
                    "negative": ["3", 0],
                    "latent_image": ["5", 0]
                },
                "class_type": "KSampler"
            },
            "5": {
                "inputs": {
                    "width": width,
                    "height": height,
                    "batch_size": 1
                },
                "class_type": "EmptyLatentImage"
            },
            "6": {
                "inputs": {
                    "samples": ["4", 0],
                    "vae": ["1", 2]
                },
                "class_type": "VAEDecode"
            },
            "7": {
                "inputs": {
                    "filename_prefix": "ComfyUI",
                    "images": ["6", 0]
                },
                "class_type": "SaveImage"
            }
        }
        
        # Queue the workflow
        result = await self.queue_prompt(workflow)
        
        if result.get("success"):
            return {
                "success": True,
                "prompt_id": result["prompt_id"],
                "client_id": result["client_id"],
                "parameters": {
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "width": width,
                    "height": height,
                    "steps": steps,
                    "cfg": cfg,
                    "seed": seed,
                    "checkpoint": checkpoint
                }
            }
        else:
            return result
    
    async def wait_for_completion(self, prompt_id: str, timeout: int = 300) -> Dict[str, Any]:
        """Wait for a prompt to complete execution"""
        start_time = asyncio.get_event_loop().time()
        
        while True:
            # Check if timeout exceeded
            if asyncio.get_event_loop().time() - start_time > timeout:
                return {
                    "success": False,
                    "error": "Timeout waiting for completion"
                }
            
            # Get history for this prompt
            history = await self.get_history(prompt_id)
            
            if prompt_id in history:
                prompt_history = history[prompt_id]
                
                # Check if completed
                if "outputs" in prompt_history:
                    return {
                        "success": True,
                        "outputs": prompt_history["outputs"],
                        "status": prompt_history.get("status", {}),
                        "prompt_id": prompt_id
                    }
                
                # Check if failed
                if "status" in prompt_history and prompt_history["status"].get("status_str") == "error":
                    return {
                        "success": False,
                        "error": prompt_history["status"].get("messages", []),
                        "prompt_id": prompt_id
                    }
            
            # Wait before checking again
            await asyncio.sleep(1)
    
    async def get_image_data(self, filename: str, subfolder: str = "", folder_type: str = "output") -> bytes:
        """Get image data from ComfyUI"""
        try:
            params = {
                "filename": filename,
                "type": folder_type
            }
            if subfolder:
                params["subfolder"] = subfolder
            
            response = await self.client.get(f"{self.base_url}/view", params=params)
            response.raise_for_status()
            return response.content
            
        except Exception as e:
            logger.error(f"Failed to get image data: {str(e)}")
            raise