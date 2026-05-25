-- 1. Create Profiles Table (Linked to Supabase Auth.users)
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    username TEXT UNIQUE,
    full_name TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable Row Level Security (RLS)
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

-- Create Policies
DROP POLICY IF EXISTS "Allow public read access to profiles" ON public.profiles;
CREATE POLICY "Allow public read access to profiles" ON public.profiles 
    FOR SELECT USING (true);

DROP POLICY IF EXISTS "Allow users to update their own profile" ON public.profiles;
CREATE POLICY "Allow users to update their own profile" ON public.profiles 
    FOR UPDATE USING (auth.uid() = id);

DROP POLICY IF EXISTS "Allow users to insert their own profile" ON public.profiles;
CREATE POLICY "Allow users to insert their own profile" ON public.profiles 
    FOR INSERT WITH CHECK (auth.uid() = id);

-- Trigger to automatically create profile on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.profiles (id, username, full_name)
  VALUES (
    new.id, 
    COALESCE(new.raw_user_meta_data->>'username', split_part(new.email, '@', 1)), 
    COALESCE(new.raw_user_meta_data->>'full_name', split_part(new.email, '@', 1))
  );
  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();


-- 2. Create User Settings Table (for API keys & selected model)
CREATE TABLE IF NOT EXISTS public.user_settings (
    user_id UUID PRIMARY KEY REFERENCES public.profiles(id) ON DELETE CASCADE,
    openai_api_key TEXT,
    anthropic_api_key TEXT,
    gemini_api_key TEXT,
    selected_provider TEXT DEFAULT 'openai',
    selected_model TEXT DEFAULT 'gpt-4o-mini',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

ALTER TABLE public.user_settings ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can manage their own settings" ON public.user_settings;
CREATE POLICY "Users can manage their own settings" ON public.user_settings 
    FOR ALL USING (auth.uid() = user_id);


-- 3. Create Prompts Table (Dynamic Templates)
CREATE TABLE IF NOT EXISTS public.prompts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    prompt_template TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

ALTER TABLE public.prompts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can manage their own prompts" ON public.prompts;
CREATE POLICY "Users can manage their own prompts" ON public.prompts 
    FOR ALL USING (auth.uid() = user_id);


-- 4. Create Extracted Documents Table (History)
CREATE TABLE IF NOT EXISTS public.extracted_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    prompt_id UUID REFERENCES public.prompts(id) ON DELETE SET NULL,
    extracted_data JSONB NOT NULL,
    raw_content_summary TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

ALTER TABLE public.extracted_documents ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view and manage their own extractions" ON public.extracted_documents;
CREATE POLICY "Users can view and manage their own extractions" ON public.extracted_documents 
    FOR ALL USING (auth.uid() = user_id);
