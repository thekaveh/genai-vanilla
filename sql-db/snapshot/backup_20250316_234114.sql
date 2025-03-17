--
-- PostgreSQL database dump
--

-- Dumped from database version 16.2 (Debian 16.2-1.pgdg110+2)
-- Dumped by pg_dump version 16.2 (Debian 16.2-1.pgdg110+2)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: llm; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.llm (
    id integer NOT NULL,
    active boolean DEFAULT false NOT NULL,
    vision boolean DEFAULT false NOT NULL,
    content boolean DEFAULT false NOT NULL,
    structured_content boolean DEFAULT false NOT NULL,
    embeddings boolean DEFAULT false NOT NULL,
    provider character varying(20) NOT NULL,
    name character varying(100)
);


ALTER TABLE public.llm OWNER TO postgres;

--
-- Data for Name: llm; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.llm (id, active, vision, content, structured_content, embeddings, provider, name) FROM stdin;
1	t	f	f	f	t	ollama	mxbai-embed-large:latest
2	t	f	t	f	f	ollama	gemma3:12b
\.


--
-- Name: llm llm_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.llm
    ADD CONSTRAINT llm_pkey PRIMARY KEY (id);


--
-- PostgreSQL database dump complete
--

