import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from supabase import create_client, Client

# Configuração da página
st.set_page_config(page_title="Controle Financeiro Familiar", page_icon="💰", layout="wide")

# Função auxiliar para formatar moeda em Reais (PT-BR)
def formatar_real(valor):
    if pd.isna(valor):
        return "R$ 0,00"
    valor_formatado = f"{float(valor):,.2f}"
    # Trocar vírgula por ponto (milhar) e ponto por vírgula (decimal)
    valor_formatado = valor_formatado.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {valor_formatado}"

# ==========================================
# SISTEMA DE LOGIN SEGURANÇA
# ==========================================
def check_password():
    def password_entered():
        usuario = st.session_state["username"]
        senha_digitada = st.session_state["password"]
        
        if "passwords" in st.secrets and usuario in st.secrets["passwords"]:
            if senha_digitada == st.secrets["passwords"][usuario]:
                st.session_state["password_correct"] = True
                del st.session_state["password"]
                st.session_state["logged_user"] = usuario
                return
                
        st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔒 Acesso Restrito")
        st.write("Por favor, faça login para acessar o Controle Financeiro.")
        st.text_input("Usuário", key="username")
        st.text_input("Senha", type="password", key="password")
        st.button("Entrar", on_click=password_entered)
        return False
        
    elif not st.session_state["password_correct"]:
        st.title("🔒 Acesso Restrito")
        st.text_input("Usuário", key="username")
        st.text_input("Senha", type="password", key="password")
        st.button("Entrar", on_click=password_entered)
        st.error("😕 Usuário ou senha incorretos!")
        return False
        
    else:
        return True

if not check_password():
    st.stop()

# ==========================================
# SISTEMA FINANCEIRO
# ==========================================

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

def carregar_dados():
    try:
        response = supabase.table("lancamentos").select("*").execute()
        dados = response.data
        if dados:
            df = pd.DataFrame(dados)
            df['data'] = pd.to_datetime(df['data'])
            # Ordenar por data mais recente
            df = df.sort_values(by="data", ascending=False)
            return df
        else:
            return pd.DataFrame(columns=[
                "id", "data", "descricao", "valor", "tipo_pgto", 
                "parcelas", "status", "tipo", "categoria", "conta_cartao"
            ])
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

df = carregar_dados()

usuario_logado = st.session_state.get("logged_user", "Usuário").capitalize()
st.sidebar.title(f"💰 Olá, {usuario_logado}!")
menu = st.sidebar.radio("Navegação", ["Dashboard", "Lançamentos", "Ver Tabela Completa", "Relatórios", "Cartões de Crédito"])

if menu == "Dashboard":
    st.title("📊 Dashboard Financeiro")
    
    if df.empty:
        st.info("Nenhum dado lançado ainda.")
    else:
        # Filtro de Ano
        df['ano'] = df['data'].dt.year
        anos_disponiveis = sorted(df['ano'].dropna().unique().tolist(), reverse=True)
        
        col_filtro, _ = st.columns([1, 3])
        with col_filtro:
            ano_selecionado = st.selectbox("Filtrar por Ano:", ["Todos"] + anos_disponiveis)
            
        if ano_selecionado != "Todos":
            df_dash = df[df['ano'] == ano_selecionado].copy()
        else:
            df_dash = df.copy()
            
        st.markdown("---")
            
        receitas = df_dash[df_dash['tipo'] == 'Crédito']['valor'].astype(float).sum()
        despesas = df_dash[df_dash['tipo'] == 'Débito']['valor'].astype(float).sum()
        saldo = receitas - despesas
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Receitas", formatar_real(receitas))
        col2.metric("Despesas", formatar_real(despesas))
        col3.metric("Saldo", formatar_real(saldo))
        
        st.markdown("---")
        
        col_graf1, col_graf2 = st.columns(2)
        
        with col_graf1:
            st.subheader("Despesas por Categoria")
            df_despesas = df_dash[df_dash['tipo'] == 'Débito'].copy()
            if not df_despesas.empty:
                df_despesas['valor'] = df_despesas['valor'].astype(float)
                fig1 = px.pie(df_despesas, values='valor', names='categoria', hole=0.4)
                st.plotly_chart(fig1, use_container_width=True)
            else:
                st.write("Sem despesas para mostrar neste ano.")
                
        with col_graf2:
            st.subheader("Gastos por Conta/Cartão")
            if not df_despesas.empty:
                fig2 = px.bar(df_despesas.groupby('conta_cartao')['valor'].sum().reset_index(), 
                              x='conta_cartao', y='valor', color='conta_cartao')
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.write("Sem dados para mostrar neste ano.")

elif menu == "Lançamentos":
    st.title("➕ Novo Lançamento")
    
    with st.form("form_lancamento", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            data = st.date_input("Data", datetime.now(), format="DD/MM/YYYY")
            descricao = st.text_input("Descrição")
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
                "Cartão Flamengo", "Cartão Itaú Black", "Cartão Credicard", "Outros"
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
                st.success("Lançamento salvo com sucesso!")
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")

elif menu == "Ver Tabela Completa":
    st.title("📋 Todos os Lançamentos")
    
    if df.empty:
        st.write("Nenhum dado lançado ainda.")
    else:
        df_exibicao = df.copy()
        # Força os dados de data a serem tratados como texto puro para o Streamlit não tentar adivinhar
        df_exibicao['data'] = df_exibicao['data'].dt.strftime('%d/%m/%Y')
        df_exibicao['valor'] = df_exibicao['valor'].apply(formatar_real)
        
        st.dataframe(df_exibicao, use_container_width=True, hide_index=True)
        
        st.write("---")
        st.write("Apagar Lançamento:")
        id_apagar = st.number_input("ID do lançamento para apagar:", min_value=0, step=1)
        if st.button("Apagar Lançamento"):
            if id_apagar > 0:
                try:
                    supabase.table("lancamentos").delete().eq("id", id_apagar).execute()
                    st.success("Apagado com sucesso! Atualize a página.")
                except Exception as e:
                    st.error("Erro ao apagar.")

elif menu == "Relatórios":
    st.title("📈 Relatórios Avançados")
    
    if df.empty:
        st.warning("Nenhum dado disponível para relatórios.")
    else:
        st.write("Utilize os filtros abaixo para gerar seu relatório:")
        
        # Filtros
        col1, col2, col3 = st.columns(3)
        
        with col1:
            data_inicio = st.date_input("Data Inicial", df['data'].min().date() if not df.empty else datetime.now().date(), format="DD/MM/YYYY")
        with col2:
            data_fim = st.date_input("Data Final", df['data'].max().date() if not df.empty else datetime.now().date(), format="DD/MM/YYYY")
        with col3:
            tipos_unicos = df['tipo'].dropna().unique().tolist()
            tipo_filtro = st.multiselect("Filtrar por Tipo", options=tipos_unicos, default=tipos_unicos)
            
        col4, col5 = st.columns(2)
        with col4:
            cat_unicas = df['categoria'].dropna().unique().tolist()
            cat_filtro = st.multiselect("Filtrar por Categoria", options=cat_unicas, default=cat_unicas)
        with col5:
            contas_unicas = df['conta_cartao'].dropna().unique().tolist()
            conta_filtro = st.multiselect("Filtrar por Conta/Cartão", options=contas_unicas, default=contas_unicas)

        # Aplicando Filtros
        df_filtrado = df[
            (df['data'].dt.date >= data_inicio) & 
            (df['data'].dt.date <= data_fim) &
            (df['tipo'].isin(tipo_filtro)) &
            (df['categoria'].isin(cat_filtro)) &
            (df['conta_cartao'].isin(conta_filtro))
        ].copy()

        st.markdown("---")
        
        # Resumo do Relatório
        st.subheader("Resumo do Filtro")
        r_receitas = df_filtrado[df_filtrado['tipo'] == 'Crédito']['valor'].astype(float).sum()
        r_despesas = df_filtrado[df_filtrado['tipo'] == 'Débito']['valor'].astype(float).sum()
        r_saldo = r_receitas - r_despesas
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total de Entradas", formatar_real(r_receitas))
        c2.metric("Total de Saídas", formatar_real(r_despesas))
        c3.metric("Saldo do Período", formatar_real(r_saldo))

        st.write(f"**Registros encontrados:** {len(df_filtrado)}")

        # Exibindo Tabela Filtrada com Formatos Corretos
        if not df_filtrado.empty:
            df_filtrado['data'] = df_filtrado['data'].dt.strftime('%d/%m/%Y')
            df_filtrado['valor'] = df_filtrado['valor'].apply(formatar_real)
            st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

elif menu == "Cartões de Crédito":
    st.title("💳 Faturas e Cartões de Crédito")
    
    if df.empty:
        st.warning("Nenhum dado disponível.")
    else:
        st.write("Veja os lançamentos separados por cada cartão, da mesma forma que você via nas abas do seu Excel.")
        
        # Identificar todos os cartões cadastrados
        contas_disponiveis = sorted(df['conta_cartao'].dropna().unique().tolist())
        
        # Filtro de Cartão
        col_cartao, _ = st.columns([1, 2])
        with col_cartao:
            cartao_selecionado = st.selectbox("Selecione o Cartão/Conta para visualizar:", contas_disponiveis)
            
        # Filtrar apenas os dados do cartão selecionado
        df_cartao = df[df['conta_cartao'] == cartao_selecionado].copy()
        
        st.markdown(f"### Resumo de: {cartao_selecionado}")
        
        # Somatório de gastos e pagamentos deste cartão
        despesas_cartao = df_cartao[df_cartao['tipo'] == 'Débito']['valor'].astype(float).sum()
        receitas_cartao = df_cartao[df_cartao['tipo'] == 'Crédito']['valor'].astype(float).sum()
        
        c1, c2 = st.columns(2)
        c1.metric("Total Gasto (Débitos)", formatar_real(despesas_cartao))
        c2.metric("Total Abatido/Pago (Créditos)", formatar_real(receitas_cartao))
        
        st.markdown("---")
        
        if not df_cartao.empty:
            df_cartao_exib = df_cartao.copy()
            df_cartao_exib['data'] = df_cartao_exib['data'].dt.strftime('%d/%m/%Y')
            df_cartao_exib['valor'] = df_cartao_exib['valor'].apply(formatar_real)
            
            st.dataframe(df_cartao_exib, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum lançamento encontrado para este cartão.")

st.sidebar.markdown("---")
if st.sidebar.button("Sair (Logout)"):
    st.session_state.clear()
    st.rerun()
st.sidebar.success("✅ Conectado ao Supabase na Nuvem!")

