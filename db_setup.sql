CREATE TABLE public.sensors (
    acp_id character varying NOT NULL,
    acp_ts TIMESTAMP,
    acp_ts_end TIMESTAMP,
    sensor_info jsonb
);

CREATE INDEX acp_id_index ON public.sensors;

INSERT INTO sensors VALUES ( 'elsys-eye-044505', to_timestamp(1591094324.12), to_timestamp(1591094334.12), '{ "foo": "bah" }');
INSERT INTO sensors VALUES ( 'elsys-eye-044504', to_timestamp(1591094323.12), to_timestamp(1591094334.12), '{ "foo": "bah" }');
INSERT INTO sensors VALUES ( 'elsys-eye-044505', to_timestamp(1591094334.12), NULL, '{ "foo": "bah" }');
INSERT INTO sensors VALUES ( 'elsys-eye-044504', to_timestamp(1591094334.12), NULL, '{ "foo": "bah" }');
