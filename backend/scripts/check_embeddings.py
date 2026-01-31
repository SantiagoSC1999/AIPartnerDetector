import os
import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    print("ERROR: Missing SUPABASE credentials")
    sys.exit(1)

client = create_client(supabase_url, supabase_key)

# Count embeddings
try:
    response = client.table('institution_embeddings').select('institution_id', count='exact').range(0, 1).execute()
    print(f'✓ Total embeddings in DB: {response.count}')
except Exception as e:
    print(f'✗ Error counting embeddings: {str(e)}')

# Count institutions  
try:
    response = client.table('clarisa_institutions').select('id', count='exact').range(0, 1).execute()
    print(f'✓ Total institutions in DB: {response.count}')
except Exception as e:
    print(f'✗ Error counting institutions: {str(e)}')
