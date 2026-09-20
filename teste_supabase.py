import os
from supabase import create_client, Client

url: str = "https://dprdbapenvxygujbueqx.supabase.co"
key: str = "sb_secret_0pYVHe482jCgOPcL_QIKXQ_IpT3001Q"

try:
    supabase: Client = create_client(url, key)
    response = supabase.table("lancamentos").select("*").execute()
    print("Sucesso! Conexao funcionou. Dados:", response.data)
except Exception as e:
    print("Erro na conexao:", e)
