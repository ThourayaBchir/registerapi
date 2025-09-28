CREATE TABLE IF NOT EXISTS activation_codes (
    id BIGSERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    code CHAR(4) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_activation_email_code UNIQUE (email, code, created_at)
);

CREATE INDEX IF NOT EXISTS idx_activation_email ON activation_codes (email);
CREATE INDEX IF NOT EXISTS idx_activation_expires_at ON activation_codes (expires_at);
