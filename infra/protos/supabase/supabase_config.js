// infra/protos/supabase/supabase_config.js
// Supabase configuration and client initialization example.

import { createClient } from "@supabase/supabase-js";

// Configure these through environment variables; never commit credentials.
const supabaseUrl = process.env.SUPABASE_URL;
const supabaseAnonKey = process.env.SUPABASE_ANON_KEY;

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

// Convenience exports mirroring the Firebase Auth/Firestore service split.
export const auth = supabase.auth;
export const db = supabase;
export const storage = supabase.storage;

export default supabase;
