-- Create analysis_records table to store analysis results
CREATE TABLE IF NOT EXISTS analysis_records (
    id BIGSERIAL PRIMARY KEY,
    file_id UUID NOT NULL,
    filename TEXT NOT NULL,
    uploaded_id TEXT NOT NULL,
    institution_name TEXT,
    acronym TEXT,
    status TEXT NOT NULL,
    similarity FLOAT DEFAULT 0,
    clarisa_match INTEGER,
    reason TEXT,
    web_page TEXT,
    type TEXT,
    country INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_analysis_file_id ON analysis_records(file_id);
CREATE INDEX IF NOT EXISTS idx_analysis_created_at ON analysis_records(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analysis_status ON analysis_records(status);
CREATE INDEX IF NOT EXISTS idx_analysis_clarisa_match ON analysis_records(clarisa_match);

-- Grant permissions if needed
-- GRANT ALL ON analysis_records TO authenticated;
