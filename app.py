import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import calendar
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

df_geral = carregar_dados()
if not df_geral.empty:
    df_config = df_geral[df_geral['tipo'] == 'Config_Cartao'].copy()
    df = df_geral[df_geral['tipo'] != 'Config_Cartao'].copy()
else:
    df_config = pd.DataFrame()
    df = df_geral

@st.dialog("✏️ Editar Lançamento")
def modal_editar_lancamento(row):
    with st.form(f"form_edit_{row['id']}"):
        e_data = st.date_input("Data", pd.to_datetime(row['data']).date(), format="DD/MM/YYYY")
        e_desc = st.text_input("Descrição", str(row['descricao']))
        e_val = st.number_input("Valor (R$)", value=float(row['valor']), min_value=0.0, format="%.2f")
        
        tipo_opts = ["Débito", "Crédito"]
        t_idx = tipo_opts.index(row['tipo']) if row['tipo'] in tipo_opts else 0
        e_tipo = st.selectbox("Tipo", tipo_opts, index=t_idx)
        
        cat_opts = ["Moradia", "Alimentação", "Transporte", "Saúde", "Estudos", "Lazer", "Veículos", "Cartões de Crédito", "Salário", "Investimentos", "Outros"]
        c_idx = cat_opts.index(row['categoria']) if row['categoria'] in cat_opts else 10
        e_cat = st.selectbox("Categoria", cat_opts, index=c_idx)
        
        pgto_opts = ["Boleto", "Pix", "Cartão de Crédito", "Cartão de Débito", "Dinheiro", "Débito em Conta"]
        p_idx = pgto_opts.index(row['tipo_pgto']) if row['tipo_pgto'] in pgto_opts else 1
        e_pgto = st.selectbox("Forma de Pagamento", pgto_opts, index=p_idx)
        
        conta_opts = ["Conta Corrente", "Mercado Pago", "Cartão PAN", "Cartão Samsung", "Cartão Flamengo", "Cartão Itaú Black", "Cartão Credicard", "Outros"]
        if not df_config.empty:
            for nc in df_config['conta_cartao'].dropna().unique().tolist():
                if nc not in conta_opts: conta_opts.append(nc)
        ct_idx = conta_opts.index(row['conta_cartao']) if row['conta_cartao'] in conta_opts else 0
        e_conta = st.selectbox("Conta / Cartão", conta_opts, index=ct_idx)
        
        st_opts = ["Pago", "Pendente"]
        s_idx = st_opts.index(row['status']) if row['status'] in st_opts else 0
        e_status = st.selectbox("Status", st_opts, index=s_idx)
        
        e_parc = st.text_input("Parcelas", value=str(row['parcelas']))
        
        if st.form_submit_button("Salvar Alterações", use_container_width=True):
            atualizacao = {
                "data": str(e_data),
                "descricao": e_desc,
                "valor": float(e_val),
                "tipo": e_tipo,
                "categoria": e_cat,
                "tipo_pgto": e_pgto,
                "conta_cartao": e_conta,
                "status": e_status,
                "parcelas": e_parc
            }
            try:
                supabase.table("lancamentos").update(atualizacao).eq("id", row['id']).execute()
                st.rerun()
            except Exception as e:
                st.error(f"Erro: {e}")

@st.dialog("⚠️ Confirmar Exclusão")
def modal_apagar_lancamento(row):
    st.write(f"Tem certeza que deseja apagar o lançamento **{row['descricao']}**?")
    st.write("Esta ação não poderá ser desfeita.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("❌ Cancelar", use_container_width=True):
            st.rerun()
    with col2:
        if st.button("🗑️ Sim, apagar", use_container_width=True, type="primary"):
            try:
                supabase.table("lancamentos").delete().eq("id", row['id']).execute()
                st.rerun()
            except Exception as e:
                st.error("Erro ao apagar.")

@st.dialog("✏️ Editar Cartão")
def modal_editar_cartao(cartao_nome, limit_atual, titular_atual):
    with st.form(f"form_edit_cartao_{cartao_nome}"):
        st.write(f"Editando configurações de **{cartao_nome}**")
        novo_titular = st.selectbox("Titular do Cartão", ["Erika", "Marcus"], index=0 if titular_atual=="Erika" else 1)
        novo_limite_str = st.text_input("Limite do Cartão (R$)", value=f"{limit_atual:.2f}".replace(".", ","))
        
        if st.form_submit_button("Salvar Alterações", type="primary"):
            try:
                limite_float = float(novo_limite_str.replace(".", "").replace(",", "."))
            except ValueError:
                st.error("Formato inválido.")
                st.stop()
            try:
                supabase.table("lancamentos").update({
                    "valor": limite_float,
                    "descricao": f"Titular: {novo_titular}",
                    "status": "Pago" # Reactivates if it was inactive
                }).eq("tipo", "Config_Cartao").eq("conta_cartao", cartao_nome).execute()
                st.rerun()
            except Exception as e:
                st.error("Erro ao atualizar cartão.")

@st.dialog("🚫 Inativar Cartão")
def modal_inativar_cartao(cartao_nome):
    lancamentos_futuros = df[(df['conta_cartao'] == cartao_nome) & (df['data'].dt.date > datetime.now().date())]
    if not lancamentos_futuros.empty:
        st.error(f"Não é possível inativar este cartão. Existem {len(lancamentos_futuros)} lançamento(s) futuro(s) cadastrado(s) para ele.")
        if st.button("OK, entendi"):
            st.rerun()
    else:
        st.write(f"Tem certeza que deseja inativar o **{cartao_nome}**?")
        st.write("Ele não aparecerá mais nas listas para novos lançamentos (faturas passadas ainda o exibirão).")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("❌ Cancelar", use_container_width=True):
                st.rerun()
        with col2:
            if st.button("🚫 Sim, inativar", use_container_width=True, type="primary"):
                try:
                    supabase.table("lancamentos").update({"status": "Inativo"}).eq("tipo", "Config_Cartao").eq("conta_cartao", cartao_nome).execute()
                    st.rerun()
                except Exception as e:
                    st.error("Erro ao inativar.")

usuario_logado = st.session_state.get("logged_user", "Usuário").capitalize()
st.sidebar.title(f"💰 Olá, {usuario_logado}!")

def page_dashboard():
    col_titulo, col_toggle = st.columns([3, 1])
    with col_titulo:
        st.title("📊 Dashboard Financeiro")
    with col_toggle:
        st.write("") # Espaçamento
        mostrar_valores = st.toggle("👁️ Mostrar Valores", value=False)
        
    def val_mask(valor):
        return formatar_real(valor) if mostrar_valores else "R$ •••••"

    if df.empty:
        st.info("Nenhum dado lançado ainda.")
        return

    df['ano'] = df['data'].dt.year
    df['mes'] = df['data'].dt.month

    anos_disponiveis = sorted(df['ano'].dropna().unique().tolist(), reverse=True)
    meses_nomes = {1:"Janeiro", 2:"Fevereiro", 3:"Março", 4:"Abril", 5:"Maio", 6:"Junho", 7:"Julho", 8:"Agosto", 9:"Setembro", 10:"Outubro", 11:"Novembro", 12:"Dezembro"}
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        ano_selecionado = st.selectbox("📅 Selecione o Ano:", anos_disponiveis, index=0)
    
    df_ano = df[df['ano'] == ano_selecionado].copy()
    meses_disponiveis = sorted(df_ano['mes'].dropna().unique().tolist())
    opcoes_mes = ["Todos os Meses"] + [meses_nomes[m] for m in meses_disponiveis]
    
    with col_f2:
        mes_str = st.selectbox("📆 Selecione o Mês:", opcoes_mes, index=0)
        
    if mes_str != "Todos os Meses":
        mes_int = [k for k, v in meses_nomes.items() if v == mes_str][0]
        df_dash = df_ano[df_ano['mes'] == mes_int].copy()
    else:
        df_dash = df_ano.copy()

    st.markdown("---")
    
    receitas = df_dash[df_dash['tipo'] == 'Crédito']['valor'].astype(float).sum()
    despesas = df_dash[df_dash['tipo'] == 'Débito']['valor'].astype(float).sum()
    saldo = receitas - despesas

    c1, c2, c3 = st.columns(3)
    c1.metric("🟢 Entradas (Receitas)", val_mask(receitas))
    c2.metric("🔴 Saídas (Despesas)", val_mask(despesas))
    c3.metric("💰 Saldo do Período", val_mask(saldo))
    
    st.markdown("---")
    
    st.subheader("📈 Evolução Financeira")
    if mes_str == "Todos os Meses":
        df_evol = df_ano.groupby(['mes', 'tipo'])['valor'].sum().reset_index()
        df_evol['mes_nome'] = df_evol['mes'].map(meses_nomes)
        df_evol = df_evol.sort_values('mes')
        
        # Ensure we have a string sequence for X axis to prevent Plotly from treating it as category improperly
        df_evol['mes_ord'] = df_evol['mes'].astype(str) + " - " + df_evol['mes_nome']
        
        fig_evol = px.line(df_evol, x='mes_nome', y='valor', color='tipo', 
                           color_discrete_map={"Crédito": "#17B169", "Débito": "#E44D2E"},
                           markers=True)
    else:
        df_dash['dia'] = df_dash['data'].dt.day
        df_evol = df_dash.groupby(['dia', 'tipo'])['valor'].sum().reset_index()
        df_evol = df_evol.sort_values('dia')
        # force day to string to show correctly as discrete
        df_evol['dia'] = df_evol['dia'].astype(str)
        fig_evol = px.bar(df_evol, x='dia', y='valor', color='tipo', barmode='group',
                          color_discrete_map={"Crédito": "#17B169", "Débito": "#E44D2E"})
                          
    fig_evol.update_layout(xaxis_title="", yaxis_title="", margin=dict(t=20, b=20, l=0, r=0))
    if not mostrar_valores:
        fig_evol.update_yaxes(showticklabels=False)
        fig_evol.update_traces(hovertemplate="R$ •••••")
    st.plotly_chart(fig_evol, use_container_width=True)

    st.markdown("---")
    
    col_g1, col_g2 = st.columns(2)
    df_despesas = df_dash[df_dash['tipo'] == 'Débito'].copy()
    
    with col_g1:
        st.subheader("🍕 Despesas por Categoria")
        if not df_despesas.empty:
            cat_sum = df_despesas.groupby('categoria')['valor'].sum().reset_index().sort_values('valor', ascending=False)
            if len(cat_sum) > 5:
                top5 = cat_sum.head(5)
                outros = pd.DataFrame([{'categoria': 'Outras', 'valor': cat_sum.iloc[5:]['valor'].sum()}])
                cat_sum = pd.concat([top5, outros], ignore_index=True)
                
            fig_cat = px.pie(cat_sum, values='valor', names='categoria', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_cat.update_traces(textposition='inside', textinfo='percent+label' if mostrar_valores else 'label')
            if not mostrar_valores:
                fig_cat.update_traces(hovertemplate="•••••")
            fig_cat.update_layout(showlegend=False, margin=dict(t=20, b=20, l=0, r=0))
            st.plotly_chart(fig_cat, use_container_width=True)
        else:
            st.info("Sem despesas no período.")
            
    with col_g2:
        st.subheader("💳 Detalhamento de Gastos (Locais)")
        if not df_despesas.empty:
            top5_contas = df_despesas.groupby('conta_cartao')['valor'].sum().nlargest(5).index
            df_gasto_det = df_despesas[df_despesas['conta_cartao'].isin(top5_contas)]
            df_gasto = df_gasto_det.groupby(['conta_cartao', 'categoria'])['valor'].sum().reset_index()
            
            ordem = df_gasto_det.groupby('conta_cartao')['valor'].sum().sort_values(ascending=True).index
            
            fig_bar = px.bar(df_gasto, x='valor', y='conta_cartao', color='categoria', orientation='h',
                             color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_bar.update_yaxes(categoryorder='array', categoryarray=ordem)
            
            if not mostrar_valores:
                fig_bar.update_xaxes(showticklabels=False)
                fig_bar.update_traces(hovertemplate="•••••")
            else:
                fig_bar.update_traces(hovertemplate="%{color}: R$ %{x:,.2f}")
                
            fig_bar.update_layout(showlegend=True, xaxis_title="", yaxis_title="", margin=dict(t=20, b=20, l=0, r=0), 
                                  legend_title="", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Sem despesas no período.")

def page_lancamentos():
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
                cartoes_configurados = []
                if not df_config.empty:
                    df_c_ativos = df_config.sort_values('data').drop_duplicates(subset=['conta_cartao'], keep='last')
                    df_c_ativos = df_c_ativos[df_c_ativos['status'] != 'Inativo']
                    cartoes_configurados = df_c_ativos['conta_cartao'].dropna().unique().tolist()
                    for nc in cartoes_configurados:
                        if nc not in conta_opts: conta_opts.append(nc)
                
                # Se for Cartão de Crédito, exibir opções focadas nisso e mudar o rótulo
                if tipo_pgto == "Cartão de Crédito":
                    opcoes_finais = [c for c in conta_opts if "Cartão" in c or c in cartoes_configurados]
                    if not opcoes_finais: opcoes_finais = conta_opts # fallback
                    rotulo_campo = "💳 Qual Cartão de Crédito?"
                else:
                    # Se for outro pagamento, exibir principalmente contas
                    opcoes_finais = [c for c in conta_opts if c not in cartoes_configurados and "Cartão" not in c]
                    if not opcoes_finais: opcoes_finais = conta_opts # fallback
                    rotulo_campo = "🏦 Conta de Saída do Dinheiro"
                    
                conta_idx = opcoes_finais.index(t.get("conta_cartao", opcoes_finais[0])) if t.get("conta_cartao", opcoes_finais[0]) in opcoes_finais else 0
                conta_cartao = st.selectbox(rotulo_campo, opcoes_finais, index=conta_idx)
            
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

        st.markdown("---")
        st.subheader("🕒 Histórico de Lançamentos")
    
        if df.empty:
            st.info("Nenhum dado lançado ainda.")
        else:
            hoje_h = datetime.now().date()
            primeiro_dia_mes_h = datetime(hoje_h.year, hoje_h.month, 1).date()
            ultimo_dia_h = calendar.monthrange(hoje_h.year, hoje_h.month)[1]
            ultimo_dia_mes_h = datetime(hoje_h.year, hoje_h.month, ultimo_dia_h).date()

            col_f1, col_f2 = st.columns(2)
            with col_f1:
                h_data_inicio = st.date_input("📅 Data Inicial", primeiro_dia_mes_h, format="DD/MM/YYYY", key="h_d_inicio")
            with col_f2:
                h_data_fim = st.date_input("📅 Data Final", ultimo_dia_mes_h, format="DD/MM/YYYY", key="h_d_fim")
            
            df_historico = df[
                (df['data'].dt.date >= h_data_inicio) & 
                (df['data'].dt.date <= h_data_fim)
            ].copy()

            st.write(f"Exibindo **{len(df_historico)}** lançamentos no período selecionado. Edite ou apague se necessário.")
        
            if df_historico.empty:
                st.warning("Nenhum lançamento encontrado neste período.")
            else:
                with st.container(height=600, border=True):
                    for _, row in df_historico.iterrows():
                        cor = ":green" if row['tipo'] == "Crédito" else ":red"
                        sinal = "+" if row['tipo'] == "Crédito" else "-"
                    
                        c1, c2, c3, c4, c5 = st.columns([1.5, 3.5, 2, 0.7, 0.7])
                        with c1:
                            data_f = row['data'].strftime('%d/%m/%Y') if pd.notna(row['data']) else ""
                            st.write(f"**{data_f}**")
                        with c2:
                            st.write(f"{row['descricao']} ({row['categoria']})")
                        with c3:
                            st.markdown(f"**{cor}[{sinal} {formatar_real(row['valor'])}]**")
                        with c4:
                            if st.button("✏️", key=f"edit_{row['id']}", help="Editar lançamento"):
                                modal_editar_lancamento(row)
                        with c5:
                            if st.button("🗑️", key=f"del_{row['id']}", help="Apagar lançamento"):
                                modal_apagar_lancamento(row)


def page_relatorios():
        st.title("📈 Relatórios Avançados")
    
        if df.empty:
            st.warning("Nenhum dado disponível para relatórios.")
        else:
            st.write("Utilize os filtros abaixo para investigar seus gastos detalhadamente:")
        
            hoje = datetime.now().date()
            primeiro_dia_mes = datetime(hoje.year, hoje.month, 1).date()
            ultimo_dia = calendar.monthrange(hoje.year, hoje.month)[1]
            ultimo_dia_mes = datetime(hoje.year, hoje.month, ultimo_dia).date()
        
        
            st.markdown("### 🔎 Filtros de Pesquisa (Geral)")
        
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                data_inicio = st.date_input("📅 Data Inicial", primeiro_dia_mes, format="DD/MM/YYYY")
            with col_d2:
                data_fim = st.date_input("📅 Data Final", ultimo_dia_mes, format="DD/MM/YYYY")
            
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                tipos_unicos = df['tipo'].dropna().unique().tolist()
                tipo_filtro = st.multiselect("📈 Tipo (Débito/Crédito)", options=tipos_unicos, default=[], placeholder="Todos os Tipos")
            with col_f2:
                cat_unicas = sorted(df['categoria'].dropna().unique().tolist())
                cat_filtro = st.multiselect("📂 Categorias", options=cat_unicas, default=[], placeholder="Todas as Categorias")
            with col_f3:
                contas_unicas = sorted(df['conta_cartao'].dropna().unique().tolist())
                conta_filtro = st.multiselect("🏦 Contas / Cartões", options=contas_unicas, default=[], placeholder="Todas as Contas")
    
            # Aplicando Filtros Base (Datas)
            df_filtrado = df[
                (df['data'].dt.date >= data_inicio) & 
                (df['data'].dt.date <= data_fim)
            ].copy()
        
            # Aplicando Filtros Dinâmicos
            if tipo_filtro:
                df_filtrado = df_filtrado[df_filtrado['tipo'].isin(tipo_filtro)]
            if cat_filtro:
                df_filtrado = df_filtrado[df_filtrado['categoria'].isin(cat_filtro)]
            if conta_filtro:
                df_filtrado = df_filtrado[df_filtrado['conta_cartao'].isin(conta_filtro)]
    
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
            
def page_cartoes():
        st.title("💳 Faturas e Cartões de Crédito")
    
        aba_faturas, aba_relatorio, aba_cadastro = st.tabs(["🧾 Ver Faturas", "📊 Relatório Consolidado", "⚙️ Gerenciar Cartões"])
    
        with aba_cadastro:
            st.subheader("Configurar Novo Cartão")
            st.write("Cadastre um novo cartão e informe seu limite para acompanhar na dashboard.")
        
            with st.form("form_novo_cartao"):
                novo_cartao_nome = st.text_input("Nome do Cartão (Ex: Cartão Nubank)")
                novo_cartao_titular = st.selectbox("Titular do Cartão", ["Erika", "Marcus"])
                novo_cartao_limite_str = st.text_input("Limite do Cartão (R$)", value="0,00", help="Use vírgula para os centavos, ex: 1500,00")
            
                if st.form_submit_button("Salvar Cartão", type="primary"):
                    if novo_cartao_nome.strip():
                        try:
                            # Converte formato brasileiro (1.500,00) para float (1500.00)
                            limite_limpo = novo_cartao_limite_str.replace(".", "").replace(",", ".")
                            limite_float = float(limite_limpo)
                        except ValueError:
                            st.error("Formato de valor inválido. Digite apenas números e vírgula.")
                            st.stop()
                            
                        dado_cartao = {
                            "data": str(datetime.now().date()),
                            "descricao": f"Titular: {novo_cartao_titular}",
                            "valor": limite_float,
                            "tipo": "Config_Cartao",
                            "categoria": "Sistema",
                            "tipo_pgto": "Sistema",
                            "conta_cartao": novo_cartao_nome.strip(),
                            "status": "Pago",
                            "parcelas": "-"
                        }
                        try:
                            supabase.table("lancamentos").insert(dado_cartao).execute()
                            st.success("✅ Cartão cadastrado com sucesso!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao cadastrar cartão: {e}")
                    else:
                        st.error("Por favor, informe o nome do cartão.")
                    
            st.markdown("---")
            st.subheader("Meus Cartões Cadastrados")
            if not df_config.empty:
                df_cards_unique = df_config.sort_values('data').drop_duplicates(subset=['conta_cartao'], keep='last')
                for _, row in df_cards_unique.iterrows():
                    titular = str(row['descricao']).replace("Titular: ", "") if "Titular: " in str(row['descricao']) else "Não informado"
                    is_inativo = row['status'] == 'Inativo'
                    
                    cc1, cc2, cc3 = st.columns([6, 1, 1])
                    with cc1:
                        if is_inativo:
                            st.write(f"🚫 ~~**{row['conta_cartao']}** (Titular: {titular}) — Limite Configurado: {formatar_real(row['valor'])}~~ (Inativo)")
                        else:
                            st.write(f"💳 **{row['conta_cartao']}** (Titular: {titular}) — Limite Configurado: {formatar_real(row['valor'])}")
                    with cc2:
                        if st.button("✏️", key=f"ec_{row['conta_cartao']}", help="Editar configurações"):
                            modal_editar_cartao(row['conta_cartao'], row['valor'], titular)
                    with cc3:
                        if not is_inativo:
                            if st.button("🚫", key=f"in_{row['conta_cartao']}", help="Inativar cartão"):
                                modal_inativar_cartao(row['conta_cartao'])
            else:
                st.info("Nenhum cartão extra configurado ainda.")

        with aba_faturas:
            if df.empty:
                st.warning("Nenhum dado disponível.")
            else:
                st.write("Veja os lançamentos separados por cada cartão.")
            
                hoje_c = datetime.now().date()
                primeiro_dia_mes_c = datetime(hoje_c.year, hoje_c.month, 1).date()
                ultimo_dia_c = calendar.monthrange(hoje_c.year, hoje_c.month)[1]
                ultimo_dia_mes_c = datetime(hoje_c.year, hoje_c.month, ultimo_dia_c).date()
            
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    data_inicio_c = st.date_input("📅 Data Inicial", primeiro_dia_mes_c, format="DD/MM/YYYY", key="c_inicio")
                with col_d2:
                    data_fim_c = st.date_input("📅 Data Final", ultimo_dia_mes_c, format="DD/MM/YYYY", key="c_fim")
            
                contas_disponiveis = set(df['conta_cartao'].dropna().unique().tolist())
                if not df_config.empty:
                    contas_disponiveis.update(df_config['conta_cartao'].dropna().unique().tolist())
                contas_disponiveis = sorted(list(contas_disponiveis))
            
                if not contas_disponiveis:
                    st.info("Nenhum cartão encontrado.")
                else:
                    titulares_dict = {}
                    if not df_config.empty:
                        df_cards_unique = df_config.sort_values('data').drop_duplicates(subset=['conta_cartao'], keep='last')
                        for _, r in df_cards_unique.iterrows():
                            tit = str(r['descricao']).replace("Titular: ", "") if "Titular: " in str(r['descricao']) else ""
                            if tit:
                                titulares_dict[r['conta_cartao']] = tit
                                
                    def format_cartao(nome):
                        t = titulares_dict.get(nome, "")
                        return f"{nome} - {t}" if t else nome
                        
                    col_cartao, _ = st.columns([1, 2])
                    with col_cartao:
                        cartao_selecionado = st.selectbox("Selecione o Cartão para visualizar:", contas_disponiveis, format_func=format_cartao)
                    
                    limite_cartao = 0.0
                    titular_cartao = "Não informado"
                    if not df_config.empty:
                        limites_cartao = df_config[df_config['conta_cartao'] == cartao_selecionado]
                        if not limites_cartao.empty:
                            last_conf = limites_cartao.sort_values('data').iloc[-1]
                            limite_cartao = float(last_conf['valor'])
                            if "Titular: " in str(last_conf['descricao']):
                                titular_cartao = str(last_conf['descricao']).replace("Titular: ", "")
                
                    df_cartao = df[
                        (df['conta_cartao'] == cartao_selecionado) &
                        (df['data'].dt.date >= data_inicio_c) & 
                        (df['data'].dt.date <= data_fim_c)
                    ].copy()
                
                    st.markdown(f"### Resumo de: {cartao_selecionado} (Titular: {titular_cartao})")
                
                    despesas_cartao = df_cartao[df_cartao['tipo'] == 'Débito']['valor'].astype(float).sum()
                    receitas_cartao = df_cartao[df_cartao['tipo'] == 'Crédito']['valor'].astype(float).sum()
                
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Total Gasto (Débitos)", formatar_real(despesas_cartao))
                    c2.metric("Total Abatido (Créditos)", formatar_real(receitas_cartao))
                
                    if limite_cartao > 0:
                        limite_livre = limite_cartao - despesas_cartao + receitas_cartao
                        c3.metric("Limite Disponível", formatar_real(limite_livre), help=f"Limite total configurado: {formatar_real(limite_cartao)}")
                    else:
                        c3.metric("Limite Disponível", "N/A", help="Cadastre o limite na aba de cadastro.")
                
                    st.markdown("---")
                
                    if not df_cartao.empty:
                        st.write("Lançamentos do período. Edite ou apague se necessário.")
                        with st.container(height=500, border=True):
                            for _, row in df_cartao.iterrows():
                                cor = ":green" if row['tipo'] == "Crédito" else ":red"
                                sinal = "+" if row['tipo'] == "Crédito" else "-"
                            
                                c1, c2, c3, c4, c5 = st.columns([1.5, 3.5, 2, 0.7, 0.7])
                                with c1:
                                    data_f = row['data'].strftime('%d/%m/%Y') if pd.notna(row['data']) else ""
                                    st.write(f"**{data_f}**")
                                with c2:
                                    st.write(f"{row['descricao']} ({row['categoria']})")
                                with c3:
                                    st.markdown(f"**{cor}[{sinal} {formatar_real(row['valor'])}]**")
                                with c4:
                                    if st.button("✏️", key=f"edit_c_{row['id']}", help="Editar lançamento"):
                                        modal_editar_lancamento(row)
                                with c5:
                                    if st.button("🗑️", key=f"del_c_{row['id']}", help="Apagar lançamento"):
                                        modal_apagar_lancamento(row)
                    else:
                        st.info("Nenhum lançamento encontrado para este cartão no período.")

        with aba_relatorio:
            st.markdown("### 🔎 Relatório Específico de Todos os Cartões")
            st.write("Filtre e analise os lançamentos consolidados de múltiplos cartões.")
            
            df_apenas_cartoes = df[df['conta_cartao'].str.contains('Cartão', case=False, na=False) | (df['tipo_pgto'].str.contains('Cartão', case=False, na=False))].copy()
            if df_apenas_cartoes.empty:
                st.warning("Nenhum dado de cartão de crédito encontrado.")
            else:
                hoje_c = datetime.now().date()
                primeiro_dia_mes_c = datetime(hoje_c.year, hoje_c.month, 1).date()
                ultimo_dia_mes_c = datetime(hoje_c.year, hoje_c.month, calendar.monthrange(hoje_c.year, hoje_c.month)[1]).date()

                c_d1, c_d2 = st.columns(2)
                with c_d1:
                    c_data_inicio = st.date_input("📅 Data Início (Relatório)", primeiro_dia_mes_c, format="DD/MM/YYYY")
                with c_d2:
                    c_data_fim = st.date_input("📅 Data Fim (Relatório)", ultimo_dia_mes_c, format="DD/MM/YYYY")
                
                c_f1, c_f2 = st.columns(2)
                with c_f1:
                    cartoes_unicos = sorted(df_apenas_cartoes['conta_cartao'].dropna().unique().tolist())
                    c_conta_filtro = st.multiselect("💳 Selecione os Cartões", options=cartoes_unicos, default=[], placeholder="Todos os Cartões")
                with c_f2:
                    c_cat_unicas = sorted(df_apenas_cartoes['categoria'].dropna().unique().tolist())
                    c_cat_filtro = st.multiselect("📂 Categorias", options=c_cat_unicas, default=[], placeholder="Todas as Categorias")
                
                df_cartoes_filtrado = df_apenas_cartoes[
                    (df_apenas_cartoes['data'].dt.date >= c_data_inicio) & 
                    (df_apenas_cartoes['data'].dt.date <= c_data_fim)
                ].copy()
                
                if c_conta_filtro:
                    df_cartoes_filtrado = df_cartoes_filtrado[df_cartoes_filtrado['conta_cartao'].isin(c_conta_filtro)]
                if c_cat_filtro:
                    df_cartoes_filtrado = df_cartoes_filtrado[df_cartoes_filtrado['categoria'].isin(c_cat_filtro)]
                
                st.markdown("---")
                c_despesas = df_cartoes_filtrado[df_cartoes_filtrado['tipo'] == 'Débito']['valor'].astype(float).sum()
                st.metric("Total Gasto nos Cartões (Período)", formatar_real(c_despesas))
                
                if not df_cartoes_filtrado.empty:
                    st.write("Lançamentos filtrados:")
                    with st.container(height=500, border=True):
                        for _, row in df_cartoes_filtrado.iterrows():
                            cor = ":green" if row['tipo'] == "Crédito" else ":red"
                            sinal = "+" if row['tipo'] == "Crédito" else "-"
                            c1, c2, c3, c4, c5 = st.columns([1.5, 3.5, 2, 0.7, 0.7])
                            with c1:
                                data_f = row['data'].strftime('%d/%m/%Y') if pd.notna(row['data']) else ""
                                st.write(f"**{data_f}**")
                            with c2:
                                st.write(f"{row['descricao']} ({row['conta_cartao']})")
                            with c3:
                                st.markdown(f"**{cor}[{sinal} {formatar_real(row['valor'])}]**")
                            with c4:
                                if st.button("✏️", key=f"edit_rel_{row['id']}"):
                                    modal_editar_lancamento(row)
                            with c5:
                                if st.button("🗑️", key=f"del_rel_{row['id']}"):
                                    modal_apagar_lancamento(row)
                else:
                    st.info("Nenhum registro encontrado com estes filtros.")


pg = st.navigation([
    st.Page(page_dashboard, title="Dashboard", icon="📊"),
    st.Page(page_lancamentos, title="Lançamentos", icon="✨"),
    st.Page(page_relatorios, title="Relatórios", icon="📈"),
    st.Page(page_cartoes, title="Cartões de Crédito", icon="💳")
])
pg.run()

st.sidebar.markdown("---")
if st.sidebar.button("Sair (Logout)"):
    st.session_state.clear()
    st.rerun()
st.sidebar.success("✅ Conectado ao Supabase na Nuvem!")

