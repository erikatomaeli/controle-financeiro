import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from supabase import create_client, Client

# Configuração da página
st.set_page_config(page_title="Controle Financeiro Familiar", page_icon="💰", layout="wide")

# ==========================================
# SISTEMA DE LOGIN SEGURANÇA
# ==========================================
def check_password():
    """Retorna True se o usuário inserir o login e senha corretos."""
    
    def password_entered():
        # Verifica se o usuário existe nos secrets e se a senha bate
        usuario = st.session_state["username"]
        senha_digitada = st.session_state["password"]
        
        # Lê os usuários e senhas do secrets
        if "passwords" in st.secrets and usuario in st.secrets["passwords"]:
            if senha_digitada == st.secrets["passwords"][usuario]:
                st.session_state["password_correct"] = True
                del st.session_state["password"]  # apaga a senha da memória por segurança
                st.session_state["logged_user"] = usuario
                return
                
        st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # Primeira vez abrindo o app, mostra o formulário
        st.title("🔒 Acesso Restrito")
        st.write("Por favor, faça login para acessar o Controle Financeiro.")
        st.text_input("Usuário", key="username")
        st.text_input("Senha", type="password", key="password")
        st.button("Entrar", on_click=password_entered)
        return False
        
    elif not st.session_state["password_correct"]:
        # Errou a senha
        st.title("🔒 Acesso Restrito")
        st.text_input("Usuário", key="username")
        st.text_input("Senha", type="password", key="password")
        st.button("Entrar", on_click=password_entered)
        st.error("😕 Usuário ou senha incorretos!")
        return False
        
    else:
        # Senha correta, libera o app
        return True

# Se o login não for válido, para o código aqui e não carrega o resto do site
if not check_password():
    st.stop()

# ==========================================
# SISTEMA FINANCEIRO (O RESTO DO SEU APP)
# ==========================================

# Conectar ao Supabase
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

# Função para carregar dados do Supabase
def carregar_dados():
    try:
        response = supabase.table("lancamentos").select("*").execute()
        dados = response.data
        if dados:
            df = pd.DataFrame(dados)
            df['data'] = pd.to_datetime(df['data'])
            return df
        else:
            return pd.DataFrame(columns=[
                "id", "data", "descricao", "valor", "tipo_pgto", 
                "parcelas", "status", "tipo", "categoria", "conta_cartao"
            ])
    except Exception as e:
        st.error(f"Erro ao carregar dados do banco: {e}")
        return pd.DataFrame()

df = carregar_dados()

# Menu lateral
usuario_logado = st.session_state.get("logged_user", "Usuário").capitalize()
st.sidebar.title(f"💰 Olá, {usuario_logado}!")
menu = st.sidebar.radio("Navegação", ["Dashboard", "Lançamentos", "Ver Tabela Completa"])

if menu == "Dashboard":
    st.title("📊 Dashboard Financeiro")
    
    if df.empty:
        st.info("Nenhum dado lançado ainda. Vá para 'Lançamentos' para começar a alimentar o banco de dados na nuvem!")
    else:
        receitas = df[df['tipo'] == 'Crédito']['valor'].astype(float).sum()
        despesas = df[df['tipo'] == 'Débito']['valor'].astype(float).sum()
        saldo = receitas - despesas
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Receitas", f"R$ {receitas:,.2f}")
        col2.metric("Despesas", f"R$ {despesas:,.2f}")
        col3.metric("Saldo", f"R$ {saldo:,.2f}")
        
        st.markdown("---")
        
        col_graf1, col_graf2 = st.columns(2)
        
        with col_graf1:
            st.subheader("Despesas por Categoria")
            df_despesas = df[df['tipo'] == 'Débito'].copy()
            if not df_despesas.empty:
                df_despesas['valor'] = df_despesas['valor'].astype(float)
                fig1 = px.pie(df_despesas, values='valor', names='categoria', hole=0.4)
                st.plotly_chart(fig1, use_container_width=True)
            else:
                st.write("Sem despesas para mostrar.")
                
        with col_graf2:
            st.subheader("Gastos por Conta/Cartão")
            if not df_despesas.empty:
                fig2 = px.bar(df_despesas.groupby('conta_cartao')['valor'].sum().reset_index(), 
                              x='conta_cartao', y='valor', color='conta_cartao')
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.write("Sem dados para mostrar.")

elif menu == "Lançamentos":
    st.title("➕ Novo Lançamento")
    st.write("Adicione uma nova receita ou despesa. Ela será salva diretamente no Supabase!")
    
    with st.form("form_lancamento", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            data = st.date_input("Data", datetime.now())
            descricao = st.text_input("Descrição (Ex: Supermercado Guanabara)")
            valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
            tipo = st.selectbox("Tipo", ["Débito", "Crédito"])
            status = st.selectbox("Status", ["Pago", "Pendente"])
            
        with col2:
            categoria = st.selectbox("Categoria", [
                "Moradia", "Alimentação", "Transporte", "Saúde", "Estudos", 
                "Lazer", "Veículos", "Cartões de Crédito", "Salário", "Investimentos", "Outros"
            ])
            tipo_pgto = st.selectbox("Tipo de Pagamento", ["Boleto", "Pix", "Cartão de Crédito", "Cartão de Débito", "Dinheiro"])
            parcelas = st.text_input("Parcelas (Ex: 1 de 10 ou '-' se não houver)", value="-")
            conta_cartao = st.selectbox("Conta / Cartão", [
                "Conta Corrente", "Mercado Pago", "Cartão PAN", "Cartão Samsung", 
                "Cartão Flamengo", "Cartão Itaú Black", "Cartão Credicard", "Tucson", "Outros"
            ])
            
        submit = st.form_submit_button("Salvar na Nuvem")
        
        if submit:
            novo_dado = {
                "data": str(data),
                "descricao": descricao,
                "valor": float(valor),
                "tipo_pgto": tipo_pgto,
                "parcelas": parcelas,
                "status": status,
                "tipo": tipo,
                "categoria": categoria,
                "conta_cartao": conta_cartao
            }
            try:
                supabase.table("lancamentos").insert(novo_dado).execute()
                st.success("Lançamento salvo com sucesso no banco de dados nas nuvens!")
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")

elif menu == "Ver Tabela Completa":
    st.title("📋 Todos os Lançamentos")
    
    if df.empty:
        st.write("Nenhum dado lançado ainda.")
    else:
        df_exibicao = df.copy()
        df_exibicao['data'] = df_exibicao['data'].dt.strftime('%d/%m/%Y')
        df_exibicao['valor'] = df_exibicao['valor'].astype(float)
        
        st.dataframe(df_exibicao.style.format({"valor": "R$ {:.2f}"}), use_container_width=True)
        
        st.write("---")
        st.write("Apagar Lançamento:")
        id_apagar = st.number_input("Digite o ID do lançamento que deseja apagar (veja na tabela acima):", min_value=0, step=1)
        if st.button("Apagar Lançamento"):
            if id_apagar > 0:
                try:
                    supabase.table("lancamentos").delete().eq("id", id_apagar).execute()
                    st.success("Apagado com sucesso! Atualize a página.")
                except Exception as e:
                    st.error("Erro ao apagar.")

st.sidebar.markdown("---")
if st.sidebar.button("Sair (Logout)"):
    st.session_state.clear()
    st.rerun()
st.sidebar.success("✅ Conectado ao Supabase na Nuvem!")
