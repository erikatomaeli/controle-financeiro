import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from supabase import create_client, Client

# Configuração da página
st.set_page_config(page_title="Financeiro Tomper", page_icon="🏦", layout="wide")

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
        col1, col2, col3 = st.columns([1, 1.5, 1])
        with col2:
            st.markdown("<h1 style='text-align: center; font-size: 4rem; margin-bottom: 0;'>🪙</h1>", unsafe_allow_html=True)
            st.markdown("<h1 style='text-align: center; font-size: 2.5rem; margin-top: 0;'>Financeiro Tomper</h1>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: gray; margin-bottom: 30px;'>Tecnologia e Controle. Identifique-se para acessar.</p>", unsafe_allow_html=True)
            
            with st.form("login_form"):
                st.text_input("👤 Usuário (Digite seu nome de acesso)", key="username", placeholder="Ex: erika", autocomplete="username")
                st.text_input("🔑 Senha (Digite sua senha secreta)", type="password", key="password", placeholder="Sua senha secreta", autocomplete="current-password")
                st.form_submit_button("Entrar no Sistema", on_click=password_entered, use_container_width=True)
        return False
        
    elif not st.session_state["password_correct"]:
        col1, col2, col3 = st.columns([1, 1.5, 1])
        with col2:
            st.markdown("<h1 style='text-align: center; font-size: 4rem; margin-bottom: 0;'>🪙</h1>", unsafe_allow_html=True)
            st.markdown("<h1 style='text-align: center; font-size: 2.5rem; margin-top: 0;'>Financeiro Tomper</h1>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: gray; margin-bottom: 30px;'>Tecnologia e Controle. Identifique-se para acessar.</p>", unsafe_allow_html=True)
            
            with st.form("login_form_error"):
                st.text_input("👤 Usuário (Digite seu nome de acesso)", key="username", placeholder="Ex: erika", autocomplete="username")
                st.text_input("🔑 Senha (Digite sua senha secreta)", type="password", key="password", placeholder="Sua senha secreta", autocomplete="current-password")
                st.form_submit_button("Entrar no Sistema", on_click=password_entered, use_container_width=True)
            st.error("😕 Usuário ou senha incorretos! Tente novamente.")
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
    col_titulo, col_toggle = st.columns([3, 1])
    with col_titulo:
        st.title("📊 Dashboard Financeiro")
    with col_toggle:
        st.write("") # Espaçamento
        mostrar_valores = st.toggle("👁️ Mostrar Valores", value=False)
    
    if df.empty:
        st.info("Nenhum dado lançado ainda.")
    else:
        # Filtro de Ano (Padrão no Ano Atual)
        df['ano'] = df['data'].dt.year
        anos_disponiveis = sorted(df['ano'].dropna().unique().tolist(), reverse=True)
        opcoes_ano = ["Todos"] + anos_disponiveis
        
        ano_atual = datetime.now().year
        default_idx = opcoes_ano.index(ano_atual) if ano_atual in opcoes_ano else 0
        
        col_filtro, _ = st.columns([1, 3])
        with col_filtro:
            ano_selecionado = st.selectbox("Filtrar por Ano:", opcoes_ano, index=default_idx)
            
        if ano_selecionado != "Todos":
            df_dash = df[df['ano'] == ano_selecionado].copy()
        else:
            df_dash = df.copy()
            
        st.markdown("---")
            
        receitas = df_dash[df_dash['tipo'] == 'Crédito']['valor'].astype(float).sum()
        despesas = df_dash[df_dash['tipo'] == 'Débito']['valor'].astype(float).sum()
        saldo = receitas - despesas
        
        # Oculta os valores se o toggle estiver desligado
        val_receitas = formatar_real(receitas) if mostrar_valores else "R$ •••••"
        val_despesas = formatar_real(despesas) if mostrar_valores else "R$ •••••"
        val_saldo = formatar_real(saldo) if mostrar_valores else "R$ •••••"
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Receitas", val_receitas)
        col2.metric("Despesas", val_despesas)
        col3.metric("Saldo", val_saldo)
        
        st.markdown("---")
        
        col_graf1, col_graf2 = st.columns(2)
        
        with col_graf1:
            st.subheader("Despesas por Categoria")
            df_despesas = df_dash[df_dash['tipo'] == 'Débito'].copy()
            if not df_despesas.empty:
                df_despesas['valor'] = df_despesas['valor'].astype(float)
                # Gráfico de Rosca moderno
                fig1 = px.pie(df_despesas, values='valor', names='categoria', hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
                
                # Ocultar % do gráfico se não estiver mostrando valores
                info_grafico = 'percent+label' if mostrar_valores else 'label'
                fig1.update_traces(textposition='inside', textinfo=info_grafico)
                
                fig1.update_layout(showlegend=False, margin=dict(t=20, b=20, l=0, r=0))
                st.plotly_chart(fig1, use_container_width=True)
            else:
                st.write("Sem despesas para mostrar neste período.")
                
        with col_graf2:
            st.subheader("Gastos por Cartão de Crédito")
            if not df_despesas.empty:
                # Filtrar apenas o que é cartão
                df_cartoes = df_despesas[df_despesas['conta_cartao'].str.contains('Cartão', case=False, na=False)].copy()
                
                if not df_cartoes.empty:
                    # Gráfico de Barras Horizontais ordenado
                    df_bar = df_cartoes.groupby('conta_cartao')['valor'].sum().reset_index().sort_values('valor', ascending=True)
                    fig2 = px.bar(df_bar, x='valor', y='conta_cartao', orientation='h', 
                                  color='conta_cartao', text='valor', color_discrete_sequence=px.colors.qualitative.Set2)
                                  
                    # Se o olho estiver ativado, mostra R$ real, se não mostra pontinhos na barra
                    formato_texto = 'R$ %{text:,.2s}' if mostrar_valores else 'R$ •••••'
                    fig2.update_traces(texttemplate=formato_texto, textposition='outside')
                    
                    fig2.update_layout(showlegend=False, xaxis_title="", yaxis_title="", margin=dict(t=20, b=20, l=0, r=0))
                    st.plotly_chart(fig2, use_container_width=True)
                else:
                    st.write("Nenhum gasto em cartão neste período.")
            else:
                st.write("Sem dados para mostrar neste período.")

elif menu == "Lançamentos":
    st.title("✨ Novo Lançamento")
    st.markdown("Cadastre suas contas manualmente ou escolha um **Atalho Rápido** para preencher tudo automaticamente!")
    
    # ---------------------------------------------------
    # ATALHOS INTELIGENTES (PREENCHIMENTO AUTOMÁTICO)
    # ---------------------------------------------------
    templates = {
        "✍️ Nenhum (Preenchimento Manual)": {},
        "⚡ Energia Elétrica (CPFL)": {"descricao": "CPFL", "categoria": "Moradia", "tipo": "Débito", "tipo_pgto": "Débito em Conta", "conta_cartao": "Conta Corrente", "status": "Pago"},
        "💧 Água (Sanasa/Sabesp)": {"descricao": "Conta de Água", "categoria": "Moradia", "tipo": "Débito", "tipo_pgto": "Débito em Conta", "conta_cartao": "Conta Corrente", "status": "Pago"},
        "🛒 Supermercado Mensal": {"descricao": "Supermercado Mensal", "categoria": "Alimentação", "tipo": "Débito", "tipo_pgto": "Cartão de Crédito", "conta_cartao": "Cartão Itaú Black", "status": "Pendente"},
        "🌐 Internet / TV": {"descricao": "Internet", "categoria": "Moradia", "tipo": "Débito", "tipo_pgto": "Pix", "conta_cartao": "Conta Corrente", "status": "Pago"},
        "⛽ Posto de Gasolina": {"descricao": "Gasolina", "categoria": "Transporte", "tipo": "Débito", "tipo_pgto": "Cartão de Crédito", "conta_cartao": "Cartão Itaú Black", "status": "Pendente"},
        "💰 Recebimento de Salário": {"descricao": "Salário Mensal", "categoria": "Salário", "tipo": "Crédito", "tipo_pgto": "Pix", "conta_cartao": "Conta Corrente", "status": "Pago"}
    }
    
    template_escolhido = st.selectbox("🎯 Lançamento Rápido (Contas Fixas e Comuns):", list(templates.keys()))
    t = templates[template_escolhido] # Puxa as definições baseadas na escolha
    
    st.markdown("---")
    
    with st.form("form_lancamento", clear_on_submit=True):
        st.subheader("📝 Detalhes do Lançamento")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📌 Informações Principais**")
            data = st.date_input("📅 Data", datetime.now(), format="DD/MM/YYYY")
            descricao = st.text_input("🏷️ Descrição", value=t.get("descricao", ""))
            valor = st.number_input("💲 Valor (R$)", min_value=0.0, format="%.2f")
            
            tipo_opts = ["Débito", "Crédito"]
            tipo_idx = tipo_opts.index(t.get("tipo", "Débito")) if t.get("tipo", "Débito") in tipo_opts else 0
            tipo = st.selectbox("📈 Tipo", tipo_opts, index=tipo_idx)
            
        with col2:
            st.markdown("**⚙️ Detalhes do Pagamento**")
            
            cat_opts = ["Moradia", "Alimentação", "Transporte", "Saúde", "Estudos", "Lazer", "Veículos", "Cartões de Crédito", "Salário", "Investimentos", "Outros"]
            cat_idx = cat_opts.index(t.get("categoria", "Outros")) if t.get("categoria", "Outros") in cat_opts else 10
            categoria = st.selectbox("📂 Categoria", cat_opts, index=cat_idx)
            
            pgto_opts = ["Boleto", "Pix", "Cartão de Crédito", "Cartão de Débito", "Dinheiro", "Débito em Conta"]
            pgto_idx = pgto_opts.index(t.get("tipo_pgto", "Pix")) if t.get("tipo_pgto", "Pix") in pgto_opts else 1
            tipo_pgto = st.selectbox("💳 Forma de Pagamento", pgto_opts, index=pgto_idx)
            
            conta_opts = ["Conta Corrente", "Mercado Pago", "Cartão PAN", "Cartão Samsung", "Cartão Flamengo", "Cartão Itaú Black", "Cartão Credicard", "Outros"]
            conta_idx = conta_opts.index(t.get("conta_cartao", "Conta Corrente")) if t.get("conta_cartao", "Conta Corrente") in conta_opts else 0
            conta_cartao = st.selectbox("🏦 Conta / Cartão", conta_opts, index=conta_idx)
            
        st.markdown("---")
        col3, col4 = st.columns(2)
        with col3:
            status_opts = ["Pago", "Pendente"]
            status_idx = status_opts.index(t.get("status", "Pago")) if t.get("status", "Pago") in status_opts else 0
            status = st.selectbox("✅ Status", status_opts, index=status_idx)
        with col4:
            parcelas = st.text_input("🔢 Parcelas (Ex: 1 de 10 ou deixe em branco)", value="-")
            
        submit = st.form_submit_button("🚀 Salvar Lançamento na Nuvem")
        
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
                st.success("✅ Lançamento salvo com sucesso!")
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
        st.write("Utilize os filtros abaixo para investigar seus gastos detalhadamente:")
        
        hoje = datetime.now().date()
        primeiro_dia_ano = datetime(hoje.year, 1, 1).date()
        
        aba_geral, aba_cartoes = st.tabs(["📊 Relatório Geral", "💳 Relatório de Cartões de Crédito"])
        
        with aba_geral:
            st.markdown("### 🔎 Filtros de Pesquisa (Geral)")
            
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                data_inicio = st.date_input("📅 Data Inicial", primeiro_dia_ano, format="DD/MM/YYYY")
            with col_d2:
                data_fim = st.date_input("📅 Data Final", hoje, format="DD/MM/YYYY")
                
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                tipos_unicos = df['tipo'].dropna().unique().tolist()
                tipo_filtro = st.multiselect("📈 Tipo (Débito/Crédito)", options=tipos_unicos, default=tipos_unicos)
            with col_f2:
                cat_unicas = sorted(df['categoria'].dropna().unique().tolist())
                cat_filtro = st.multiselect("📂 Categorias", options=cat_unicas, default=cat_unicas)
            with col_f3:
                # Na visão geral, podemos ocultar os cartões de crédito ou deixá-los desmarcados por padrão, mas manteremos todos para não perder dados.
                contas_unicas = sorted(df['conta_cartao'].dropna().unique().tolist())
                conta_filtro = st.multiselect("🏦 Contas / Cartões", options=contas_unicas, default=contas_unicas)
    
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
            st.subheader("📊 Resumo do Período Selecionado")
            r_receitas = df_filtrado[df_filtrado['tipo'] == 'Crédito']['valor'].astype(float).sum()
            r_despesas = df_filtrado[df_filtrado['tipo'] == 'Débito']['valor'].astype(float).sum()
            r_saldo = r_receitas - r_despesas
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Total de Entradas", formatar_real(r_receitas))
            c2.metric("Total de Saídas", formatar_real(r_despesas))
            c3.metric("Saldo do Período", formatar_real(r_saldo))
    
            st.markdown("---")
            st.subheader(f"📋 Resultados Encontrados ({len(df_filtrado)} registros)")
    
            # Exibindo Tabela Filtrada com Estilo (Verde/Vermelho)
            if not df_filtrado.empty:
                df_filtrado['data'] = df_filtrado['data'].dt.strftime('%d/%m/%Y')
                df_filtrado['valor_str'] = df_filtrado['valor'].apply(formatar_real)
                
                # Organizando colunas para ficar mais clean
                colunas_exibicao = ['data', 'descricao', 'categoria', 'conta_cartao', 'tipo_pgto', 'tipo', 'status', 'valor_str']
                df_exibicao = df_filtrado[colunas_exibicao].copy()
                
                # Renomeando colunas para exibição bonita
                df_exibicao.columns = ['Data', 'Descrição', 'Categoria', 'Conta/Cartão', 'Pagamento', 'Tipo', 'Status', 'Valor']
    
                # Função para colorir a linha baseado no tipo
                def color_rows(row):
                    color = '#17B169' if row['Tipo'] == 'Crédito' else '#E44D2E'
                    return [f'color: {color}; font-weight: 500' if col == 'Valor' else '' for col in row.index]
    
                # Aplica o estilo e exibe no Streamlit
                styled_df = df_exibicao.style.apply(color_rows, axis=1)
                st.dataframe(styled_df, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum registro encontrado com estes filtros.")
                
        with aba_cartoes:
            st.markdown("### 🔎 Relatório Específico de Cartões de Crédito")
            st.write("Filtre e analise apenas os lançamentos feitos em cartões.")
            
            # Identifica apenas contas que têm a palavra "Cartão" no nome ou tipo_pgto == "Cartão de Crédito"
            df_apenas_cartoes = df[df['conta_cartao'].str.contains('Cartão', case=False, na=False) | (df['tipo_pgto'].str.contains('Cartão', case=False, na=False))].copy()
            
            if df_apenas_cartoes.empty:
                st.warning("Nenhum dado de cartão de crédito encontrado.")
            else:
                c_d1, c_d2 = st.columns(2)
                with c_d1:
                    c_data_inicio = st.date_input("📅 Data Início (Cartões)", primeiro_dia_ano, format="DD/MM/YYYY")
                with c_d2:
                    c_data_fim = st.date_input("📅 Data Fim (Cartões)", hoje, format="DD/MM/YYYY")
                    
                c_f1, c_f2 = st.columns(2)
                with c_f1:
                    cartoes_unicos = sorted(df_apenas_cartoes['conta_cartao'].dropna().unique().tolist())
                    c_conta_filtro = st.multiselect("💳 Selecione os Cartões", options=cartoes_unicos, default=cartoes_unicos)
                with c_f2:
                    c_cat_unicas = sorted(df_apenas_cartoes['categoria'].dropna().unique().tolist())
                    c_cat_filtro = st.multiselect("📂 Categorias (Cartões)", options=c_cat_unicas, default=c_cat_unicas)
                    
                df_cartoes_filtrado = df_apenas_cartoes[
                    (df_apenas_cartoes['data'].dt.date >= c_data_inicio) & 
                    (df_apenas_cartoes['data'].dt.date <= c_data_fim) &
                    (df_apenas_cartoes['conta_cartao'].isin(c_conta_filtro)) &
                    (df_apenas_cartoes['categoria'].isin(c_cat_filtro))
                ].copy()
                
                st.markdown("---")
                # Resumo
                c_despesas = df_cartoes_filtrado[df_cartoes_filtrado['tipo'] == 'Débito']['valor'].astype(float).sum()
                st.metric("Total Gasto nos Cartões (Período)", formatar_real(c_despesas))
                
                if not df_cartoes_filtrado.empty:
                    df_cartoes_filtrado['data'] = df_cartoes_filtrado['data'].dt.strftime('%d/%m/%Y')
                    df_cartoes_filtrado['valor_str'] = df_cartoes_filtrado['valor'].apply(formatar_real)
                    
                    c_colunas_exib = ['data', 'descricao', 'categoria', 'conta_cartao', 'status', 'valor_str']
                    df_c_exib = df_cartoes_filtrado[c_colunas_exib].copy()
                    df_c_exib.columns = ['Data', 'Descrição', 'Categoria', 'Cartão', 'Status', 'Valor']
                    
                    st.dataframe(df_c_exib, use_container_width=True, hide_index=True)
                else:
                    st.info("Nenhum registro encontrado para os cartões e período selecionados.")

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

