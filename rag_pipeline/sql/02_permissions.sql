CREATE TABLE IF NOT EXISTS app_users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    display_name  TEXT,
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_app_users_email_ci
    ON app_users (LOWER(email));

CREATE TABLE IF NOT EXISTS rag_classifications (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE IF NOT EXISTS rag_roles (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE IF NOT EXISTS rag_role_classifications (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id           UUID NOT NULL REFERENCES rag_roles(id) ON DELETE CASCADE,
    classification_id UUID NOT NULL REFERENCES rag_classifications(id) ON DELETE CASCADE,
    valid_from        TIMESTAMP NOT NULL DEFAULT NOW(),
    valid_to          TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app_user_roles (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
    role_id    UUID NOT NULL REFERENCES rag_roles(id) ON DELETE CASCADE,
    valid_from TIMESTAMP NOT NULL DEFAULT NOW(),
    valid_to   TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_role_classification_open
    ON rag_role_classifications (role_id, classification_id)
    WHERE valid_to IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_user_role_open
    ON app_user_roles (user_id, role_id)
    WHERE valid_to IS NULL;

-- The original lab schema used TEXT for this optional field.  Convert it once
-- before adding the foreign key; NULL remains intentionally inaccessible.
DO $$
DECLARE
    column_type TEXT;
BEGIN
    SELECT data_type INTO column_type
      FROM information_schema.columns
     WHERE table_schema = current_schema()
       AND table_name = 'rag_documents'
       AND column_name = 'classification_id';
    IF column_type = 'text' THEN
        ALTER TABLE rag_documents
            ALTER COLUMN classification_id TYPE UUID
            USING CASE
                WHEN classification_id ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
                THEN classification_id::uuid
                ELSE NULL
            END;
    END IF;
END $$;

ALTER TABLE rag_documents
    ADD COLUMN IF NOT EXISTS created_by UUID,
    ADD COLUMN IF NOT EXISTS updated_by UUID;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'rag_documents_classification_fk'
    ) THEN
        ALTER TABLE rag_documents
            ADD CONSTRAINT rag_documents_classification_fk
            FOREIGN KEY (classification_id) REFERENCES rag_classifications(id);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'rag_documents_created_by_fk'
    ) THEN
        ALTER TABLE rag_documents
            ADD CONSTRAINT rag_documents_created_by_fk
            FOREIGN KEY (created_by) REFERENCES app_users(id);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'rag_documents_updated_by_fk'
    ) THEN
        ALTER TABLE rag_documents
            ADD CONSTRAINT rag_documents_updated_by_fk
            FOREIGN KEY (updated_by) REFERENCES app_users(id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS rag_documents_classification_idx
    ON rag_documents (classification_id);
CREATE INDEX IF NOT EXISTS app_user_roles_active_idx
    ON app_user_roles (user_id, valid_to, valid_from);
CREATE INDEX IF NOT EXISTS rag_role_classifications_active_idx
    ON rag_role_classifications (role_id, valid_to, valid_from);

CREATE OR REPLACE VIEW v_user_classifications AS
SELECT DISTINCT
    ur.user_id,
    c.id AS classification_id,
    c.name AS classification_name
FROM app_user_roles ur
JOIN rag_roles r ON r.id = ur.role_id
JOIN rag_role_classifications rc ON rc.role_id = r.id
JOIN rag_classifications c ON c.id = rc.classification_id
WHERE NOW() >= ur.valid_from
  AND (ur.valid_to IS NULL OR ur.valid_to > NOW())
  AND NOW() >= rc.valid_from
  AND (rc.valid_to IS NULL OR rc.valid_to > NOW());

INSERT INTO rag_classifications (name, description) VALUES
    ('A', 'Chung — mọi vai trò đã đăng nhập đều đọc được'),
    ('B', 'Nội bộ — chỉ manager và admin'),
    ('C', 'Mật — chỉ admin')
ON CONFLICT (name) DO NOTHING;

INSERT INTO rag_roles (name, description) VALUES
    ('staff', 'Đọc phân loại A'),
    ('manager', 'Đọc A và B'),
    ('admin', 'Đọc A, B và C')
ON CONFLICT (name) DO NOTHING;

-- Partial unique indexes cannot be ON CONFLICT arbiters, so seed mappings
-- with an explicit NOT EXISTS check and keep revoked history intact.
INSERT INTO rag_role_classifications (role_id, classification_id)
SELECT r.id, c.id
FROM rag_roles r
JOIN rag_classifications c ON (
    (r.name = 'staff' AND c.name = 'A') OR
    (r.name = 'manager' AND c.name IN ('A', 'B')) OR
    (r.name = 'admin' AND c.name IN ('A', 'B', 'C'))
)
WHERE NOT EXISTS (
    SELECT 1
    FROM rag_role_classifications existing
    WHERE existing.role_id = r.id
      AND existing.classification_id = c.id
      AND existing.valid_to IS NULL
);
