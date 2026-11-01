CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TYPE user_role AS ENUM ('0', '1', '2', '3');

CREATE TYPE contract_status AS ENUM ('pending', 'uploaded', 'processing', 'completed', 'error');

CREATE TYPE risk_level AS ENUM ('none', 'low', 'medium', 'high', 'critical');

CREATE TYPE clause_relation_type AS ENUM (
  'contradiction',
  'dependency',
  'duplicity',
  'reference_to_absent_clause'
);

CREATE TYPE severity_level AS ENUM ('low', 'medium', 'high');


CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  first_name VARCHAR(100) NOT NULL,
  last_name VARCHAR(100) NOT NULL,
  company_name VARCHAR(255),
  profile_image_url TEXT,
  role user_role DEFAULT '1',
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_login TIMESTAMP
);

CREATE TABLE legal_acceptances (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL,
  terms_version VARCHAR(50) NOT NULL,
  privacy_version VARCHAR(50) NOT NULL,
  accepted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX idx_legal_acceptances_user_id ON legal_acceptances(user_id);

CREATE TABLE user_settings (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL UNIQUE,
  theme VARCHAR(10) DEFAULT 'light' CHECK (theme IN ('light', 'dark')),
  language VARCHAR(5) DEFAULT 'es' CHECK (language IN ('es', 'en', 'fr', 'de', 'pt')),
  currency VARCHAR(3) DEFAULT 'EUR' CHECK (currency IN ('EUR', 'USD', 'GBP', 'JPY', 'CNY', 'CHF', 'CAD', 'AUD')),
  email_notifications BOOLEAN DEFAULT true,
  push_notifications BOOLEAN DEFAULT false,
  allow_analytics BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE sessions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL,
  token VARCHAR(500) UNIQUE NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  ip_address VARCHAR(45),
  user_agent TEXT,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE notifications (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL,
  title VARCHAR(255) NOT NULL,
  message TEXT NOT NULL,
  notification_type VARCHAR(50) DEFAULT 'info' CHECK (notification_type IN ('info', 'warning', 'error', 'success')),
  is_read BOOLEAN DEFAULT false,
  related_entity_type VARCHAR(50),
  related_entity_id VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE contracts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL,
  original_file_name VARCHAR(255) NOT NULL,
  storage_path TEXT NOT NULL,
  mime_type VARCHAR(100),
  file_size_bytes BIGINT,
  page_count INTEGER,
  status contract_status DEFAULT 'pending',
  overall_risk risk_level DEFAULT 'none',
  language VARCHAR(10),
  contract_type VARCHAR(100),
  uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  processed_at TIMESTAMP,
  error_message TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE contract_analyses (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  contract_id UUID NOT NULL,
  analysis_version VARCHAR(50) DEFAULT 'contract-analysis-v2',
  status contract_status DEFAULT 'processing',
  overall_risk risk_level DEFAULT 'none',
  summary TEXT,
  tokens_used INTEGER,
  started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  finished_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (contract_id) REFERENCES contracts(id) ON DELETE CASCADE
);

CREATE TABLE contract_clauses (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  analysis_id UUID NOT NULL,
  clause_number VARCHAR(50),
  title VARCHAR(255),
  original_text TEXT NOT NULL,
  plain_explanation TEXT,
  legal_advice TEXT,
  risk_level risk_level DEFAULT 'none',
  has_issue BOOLEAN DEFAULT FALSE,
  order_index INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (analysis_id) REFERENCES contract_analyses(id)
    ON DELETE CASCADE
);

CREATE TABLE contract_risks (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  analysis_id UUID NOT NULL,
  clause_id UUID,
  title VARCHAR(255) NOT NULL,
  description TEXT,
  severity severity_level NOT NULL,
  category VARCHAR(100),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (analysis_id) REFERENCES contract_analyses(id) ON DELETE CASCADE,
  FOREIGN KEY (clause_id) REFERENCES contract_clauses(id) ON DELETE SET NULL
);

CREATE TYPE aspect_type AS ENUM ('positive', 'negative');

CREATE TABLE contract_aspects (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  analysis_id UUID NOT NULL,
  clause_id UUID,
  title VARCHAR(255) NOT NULL,
  description TEXT,
  type aspect_type NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (analysis_id) REFERENCES contract_analyses(id) ON DELETE CASCADE,
  FOREIGN KEY (clause_id) REFERENCES contract_clauses(id) ON DELETE SET NULL
);

CREATE TABLE contract_missing_elements (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  analysis_id UUID NOT NULL,
  title VARCHAR(255) NOT NULL,
  description TEXT,
  suggested_clause TEXT,
  severity severity_level NOT NULL,
  category VARCHAR(100),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (analysis_id) REFERENCES contract_analyses(id) ON DELETE CASCADE
);

CREATE TABLE contract_analysis_evidence (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  analysis_id UUID NOT NULL REFERENCES contract_analyses(id) ON DELETE CASCADE,
  chunk_id VARCHAR(255),
  citation VARCHAR(500) NOT NULL,
  law_name VARCHAR(255),
  law_key VARCHAR(100),
  article_number VARCHAR(100),
  text_hash VARCHAR(128),
  score DOUBLE PRECISION,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE clause_relations (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  analysis_id UUID NOT NULL,
  type clause_relation_type NOT NULL,
  from_clause_id UUID NOT NULL,
  to_clause_id UUID,
  missing_element_id UUID,
  severity severity_level NOT NULL,
  title VARCHAR(255) NOT NULL,
  description TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (analysis_id) REFERENCES contract_analyses(id) ON DELETE CASCADE,
  FOREIGN KEY (from_clause_id) REFERENCES contract_clauses(id) ON DELETE CASCADE,
  FOREIGN KEY (to_clause_id) REFERENCES contract_clauses(id) ON DELETE SET NULL,
  FOREIGN KEY (missing_element_id) REFERENCES contract_missing_elements(id) ON DELETE SET NULL
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_token ON sessions(token);
CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_is_read ON notifications(user_id, is_read);
CREATE INDEX idx_notifications_created_at ON notifications(created_at DESC);
CREATE INDEX idx_contracts_user_id ON contracts(user_id);
CREATE INDEX idx_contracts_status ON contracts(status);
CREATE INDEX idx_contracts_uploaded_at ON contracts(uploaded_at DESC);
CREATE INDEX idx_contract_clauses_analysis_id ON contract_clauses(analysis_id);
CREATE INDEX idx_contract_clauses_number ON contract_clauses(clause_number); 
CREATE INDEX idx_contract_analyses_contract_id ON contract_analyses(contract_id);
CREATE INDEX idx_contract_analyses_status ON contract_analyses(status);
CREATE INDEX idx_contract_risks_analysis_id ON contract_risks(analysis_id);
CREATE INDEX idx_contract_risks_severity ON contract_risks(severity);
CREATE INDEX idx_aspects_analysis_id ON contract_aspects(analysis_id);
CREATE INDEX idx_aspects_type ON contract_aspects(type);
CREATE INDEX idx_missing_elements_analysis_id ON contract_missing_elements(analysis_id);
CREATE INDEX idx_contract_analysis_evidence_analysis_id ON contract_analysis_evidence(analysis_id);
CREATE INDEX idx_clause_relations_analysis_id ON clause_relations(analysis_id);
CREATE INDEX idx_clause_relations_type ON clause_relations(type);


CREATE TABLE agent_conversations (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL,
  title VARCHAR(255) DEFAULT 'Nueva conversación',
  contract_id UUID REFERENCES contracts(id) ON DELETE SET NULL,
  generated_contract_id UUID,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);



CREATE TABLE agent_messages (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  conversation_id UUID NOT NULL,
  role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
  content TEXT NOT NULL,
  contract_name VARCHAR(255) DEFAULT NULL,
  request_id UUID,
  status VARCHAR(20) NOT NULL DEFAULT 'completed' CHECK (status IN ('completed', 'error')),
  prompt_version VARCHAR(100),
  model_name VARCHAR(100),
  input_tokens INTEGER,
  output_tokens INTEGER,
  evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
  limitations JSONB NOT NULL DEFAULT '[]'::jsonb,
  abstained BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (conversation_id) REFERENCES agent_conversations(id) ON DELETE CASCADE
);



CREATE INDEX idx_agent_conversations_user_id ON agent_conversations(user_id);
CREATE INDEX idx_agent_conversations_updated_at ON agent_conversations(updated_at DESC);
CREATE INDEX idx_agent_messages_conversation_id ON agent_messages(conversation_id);
CREATE INDEX idx_agent_messages_created_at ON agent_messages(created_at);
CREATE UNIQUE INDEX uq_agent_messages_request_role
ON agent_messages(conversation_id, request_id, role) WHERE request_id IS NOT NULL;

CREATE TABLE agent_chat_requests (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  conversation_id UUID NOT NULL REFERENCES agent_conversations(id) ON DELETE CASCADE,
  request_id UUID NOT NULL,
  status VARCHAR(20) NOT NULL CHECK (status IN ('processing', 'completed', 'error')),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (conversation_id, request_id)
);

CREATE INDEX idx_agent_chat_requests_conversation ON agent_chat_requests(conversation_id);


CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = CURRENT_TIMESTAMP;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION create_default_user_settings()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO user_settings (user_id)
  VALUES (NEW.id);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_settings_updated_at BEFORE UPDATE ON user_settings
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER create_user_settings_on_register AFTER INSERT ON users
  FOR EACH ROW EXECUTE FUNCTION create_default_user_settings();

CREATE TRIGGER update_contract_clauses_updated_at
BEFORE UPDATE ON contract_clauses
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_contracts_updated_at
BEFORE UPDATE ON contracts
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_contract_analyses_updated_at
BEFORE UPDATE ON contract_analyses
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_contract_risks_updated_at
BEFORE UPDATE ON contract_risks
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_aspects_updated_at
BEFORE UPDATE ON contract_aspects
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_missing_elements_updated_at
BEFORE UPDATE ON contract_missing_elements
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_clause_relations_updated_at
BEFORE UPDATE ON clause_relations
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_agent_conversations_updated_at
BEFORE UPDATE ON agent_conversations
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_agent_chat_requests_updated_at
BEFORE UPDATE ON agent_chat_requests
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE generated_contracts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL,
  title VARCHAR(255) NOT NULL,
  contract_type VARCHAR(100) NOT NULL,
  country VARCHAR(100) DEFAULT 'España',
  language VARCHAR(50) DEFAULT 'Español',
  tone VARCHAR(50) DEFAULT 'Legal Formal',
  status VARCHAR(50) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'error')),
  current_content TEXT,
  contract_details JSONB,
  error_message VARCHAR(1000),
  generation_prompt_version VARCHAR(100),
  model_name VARCHAR(100),
  generation_started_at TIMESTAMP,
  generation_finished_at TIMESTAMP,
  usage_counted_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE generated_contract_versions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  contract_id UUID NOT NULL,
  version_number INTEGER NOT NULL CHECK (version_number > 0),
  content TEXT NOT NULL,
  change_type VARCHAR(50) NOT NULL CHECK (change_type IN ('Manual', 'IA')),
  change_description TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (contract_id) REFERENCES generated_contracts(id) ON DELETE CASCADE
);

ALTER TABLE agent_conversations
ADD CONSTRAINT fk_agent_conversation_generated_contract
FOREIGN KEY (generated_contract_id) REFERENCES generated_contracts(id) ON DELETE SET NULL;

CREATE INDEX idx_generated_contracts_user_id ON generated_contracts(user_id);
CREATE INDEX idx_generated_contracts_updated_at ON generated_contracts(updated_at DESC);
CREATE INDEX idx_generated_contract_versions_contract_id ON generated_contract_versions(contract_id);
CREATE INDEX idx_generated_contract_versions_created_at ON generated_contract_versions(created_at DESC);
CREATE UNIQUE INDEX uq_generated_contract_versions_number ON generated_contract_versions(contract_id, version_number);

CREATE TRIGGER update_generated_contracts_updated_at
BEFORE UPDATE ON generated_contracts
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TABLE user_monthly_usage (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL,
  period_start DATE NOT NULL,
  contracts_generated INTEGER DEFAULT 0,
  contracts_analyzed INTEGER DEFAULT 0,
  ai_modifications JSONB DEFAULT '{}'::jsonb,
  generation_limit_reached_at TIMESTAMP DEFAULT NULL,
  analysis_limit_reached_at TIMESTAMP DEFAULT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  UNIQUE (user_id, period_start)
);

CREATE INDEX idx_user_monthly_usage_user_period ON user_monthly_usage(user_id, period_start);

CREATE TRIGGER update_user_monthly_usage_updated_at
BEFORE UPDATE ON user_monthly_usage
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
