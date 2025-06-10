
------------------------------------------------------------------------------------------------

CREATE TABLE public.rad_downloads
(
    prod_code varchar NOT NULL,
    prod_creation_date timestamp with time zone NOT NULL,
    prod_download_date timestamp with time zone,
    prod_filename varchar,
    CONSTRAINT rad_downloads_pk PRIMARY KEY (prod_code, prod_creation_date)
);

------------------------------------------------------------------------------------------------

CREATE TABLE public.obs_providers
(
    provider_name varchar,
    network_list varchar,
    dt_fore_hours integer,
    dt_back_hours integer,
    CONSTRAINT obs_providers_provider_name_key UNIQUE (provider_name)
);

CREATE TABLE public.obs_bufr_check
(
    id serial,
    bufr_filename varchar(255),
    err_code integer,
    err_log varchar(255),
    cmd_log varchar(1000),
    datetime timestamp with time zone
);

------------------------------------------------------------------------------------------------

CREATE TABLE public.dpcn_anagrafica
(
    db varchar,
    sensore varchar,
    sensorenome varchar,
    lat double precision,
    lon double precision,
    sensoretipo varchar,
    alt double precision,
    uom varchar,
    regione varchar
);

CREATE TABLE public.dpcn_logfile
(
    fileid bigserial,
    filename varchar UNIQUE NOT NULL,
    ts_download timestamp with time zone,
    ts_ingestion timestamp with time zone,
    ts_delete timestamp with time zone,
    ts_errore timestamp with time zone,
    ms_errore varchar,
    CONSTRAINT pk_dpcn_logfile PRIMARY KEY (fileid)
);

CREATE TABLE public.dpcn_1h_aggr_logfile
(
    fileid bigint NOT NULL REFERENCES public.dpcn_logfile,
    filename varchar UNIQUE NOT NULL,
    ts_ingestion timestamp with time zone,
    ts_delete timestamp with time zone,
    ts_errore timestamp with time zone,
    ms_errore varchar
);

CREATE TABLE public.dpcn_dati
(
    fileid bigint NOT NULL REFERENCES public.dpcn_logfile,
    db varchar,
    sensore varchar,
    giorno varchar,
    orarioutc varchar,
    misura double precision
);

CREATE INDEX dpcn_dati_fileid_idx ON public.dpcn_dati(fileid);

------------------------------------------------------------------------------------------------

CREATE TABLE public.metn_anagrafica
(
    codice varchar,
    nome varchar,
    nomebreve varchar,
    quota integer,
    latitudine double precision,
    longitudine double precision,
    east double precision,
    north double precision,
    inizio varchar,
    fine varchar
);

CREATE TABLE public.metn_logdata
(
    batchid bigserial,
    batchutc varchar NOT NULL,
    codice varchar NOT NULL,
    dataora_last varchar,
    ts_download timestamp with time zone,
    ts_ingestion timestamp with time zone,
    ts_delete timestamp with time zone,
    ts_errore timestamp with time zone,
    ms_errore varchar,
    CONSTRAINT pk_metn_logdata PRIMARY KEY (batchid)
);

CREATE TABLE public.metn_dati
(
    batchid bigint NOT NULL REFERENCES public.metn_logdata,
    tipo varchar,
    dataora varchar,
    misura double precision
);

CREATE INDEX metn_dati_batchid_idx ON public.metn_dati(batchid);

CREATE TABLE public.metn_loganag
(
    id bigserial,
    ts_download timestamp with time zone,
    ts_errore timestamp with time zone,
    ms_errore varchar,
    CONSTRAINT pk_metn_loganag PRIMARY KEY (id)
);

------------------------------------------------------------------------------------------------
