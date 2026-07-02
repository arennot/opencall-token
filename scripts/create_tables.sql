CREATE TABLE opportunities (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  title TEXT NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('opencall', 'residency', 'grant')),
  organization TEXT NOT NULL,
  deadline DATE,
  location TEXT,
  disciplines TEXT[] DEFAULT '{}',
  funding TEXT,
  description TEXT,
  url TEXT,
  source TEXT NOT NULL DEFAULT 'manual',
  posted_at DATE DEFAULT CURRENT_DATE,
  featured BOOLEAN DEFAULT false,
  is_local BOOLEAN DEFAULT false,
  status TEXT DEFAULT 'published' CHECK (status IN ('draft', 'published')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE opportunities ADD COLUMN search_vector tsvector
  GENERATED ALWAYS AS (
    to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(description, '') || ' ' || coalesce(organization, ''))
  ) STORED;

CREATE INDEX idx_opportunities_search ON opportunities USING GIN(search_vector);
CREATE INDEX idx_opportunities_type ON opportunities(type);
CREATE INDEX idx_opportunities_deadline ON opportunities(deadline);
CREATE INDEX idx_opportunities_source ON opportunities(source);
CREATE INDEX idx_opportunities_posted_at ON opportunities(posted_at DESC);

ALTER TABLE opportunities ENABLE ROW LEVEL SECURITY;

CREATE POLICY "anon_can_read_published" ON opportunities
  FOR SELECT TO anon USING (status = 'published');

CREATE POLICY "anon_can_submit_local" ON opportunities
  FOR INSERT TO anon
  WITH CHECK (is_local = true AND status = 'draft' AND source = 'community');

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_opportunities_updated_at
  BEFORE UPDATE ON opportunities
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at();
