-- What-if scenarios and optimisation configs (PostgreSQL)

CREATE TABLE IF NOT EXISTS what_if_scenarios (
    id SERIAL PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES jobs(id),
    name TEXT,
    scenario_payload JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_what_if_scenarios_job_id
    ON what_if_scenarios (job_id);
CREATE INDEX IF NOT EXISTS ix_what_if_scenarios_created_at
    ON what_if_scenarios (created_at);

CREATE TABLE IF NOT EXISTS optimisations (
    id SERIAL PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES jobs(id),
    name TEXT,
    optimisation_payload JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_optimisations_job_id
    ON optimisations (job_id);
CREATE INDEX IF NOT EXISTS ix_optimisations_created_at
    ON optimisations (created_at);
