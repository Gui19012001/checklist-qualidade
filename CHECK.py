import streamlit as st
import pandas as pd
import datetime
import os
from io import BytesIO

# Lista de itens a verificar
itens = ["Etiqueta", "Tambor + Parafuso", "Solda", "Pintura", "Borracha ABS"]

# Usuários cadastrados
usuarios = {
    "joao": "1234",
    "maria": "abcd",
    "admin": "admin"
}

# Pasta e arquivo diário
PASTA = "Checklists"
if not os.path.exists(PASTA):
    os.makedirs(PASTA)

ARQUIVO_DIARIO = os.path.join(PASTA, f"Checklist_{datetime.date.today().strftime('%Y%m%d')}.xlsx")

# --- Funções ---
def login():
    st.session_state['logged_in'] = False
    with st.form("login_form", clear_on_submit=False):
        st.subheader("Login")
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar")
        if submitted:
            if usuario in usuarios and usuarios[usuario] == senha:
                st.session_state['logged_in'] = True
                st.session_state['usuario'] = usuario
            else:
                st.error("Usuário ou senha inválidos!")

def salvar_checklist(serie, resultados, usuario, foto_etiqueta=None, reinspecao=False):
    # Verificar duplicidade
    if os.path.exists(ARQUIVO_DIARIO):
        df_existente = pd.read_excel(ARQUIVO_DIARIO)
        if not reinspecao and serie in df_existente["Nº Série"].unique():
            st.error("⚠️ INVÁLIDO! DUPLICIDADE – Este Nº de Série já foi inspecionado.")
            return None, None
    else:
        df_existente = pd.DataFrame()

    dados = []
    reprovado = any(info['status'] == "Não Conforme" for info in resultados.values())

    # Salvar foto da etiqueta se existir
    caminho_foto = ""
    if foto_etiqueta is not None:
        caminho_foto = os.path.join(PASTA, f"FotoEtiqueta_{serie}_{datetime.datetime.now().strftime('%H%M%S')}.png")
        with open(caminho_foto, "wb") as f:
            f.write(foto_etiqueta.getbuffer())

    for item, info in resultados.items():
        dados.append({
            "Nº Série": serie,
            "Item": item,
            "Status": info['status'],
            "Observações": info['obs'],
            "Inspetor": usuario,
            "Data/Hora": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
            "Produto Reprovado": "Sim" if reprovado else "Não",
            "Reinspeção": "Sim" if reinspecao else "Não",
            "Foto Etiqueta": caminho_foto if item == "Etiqueta" else ""
        })

    df_novo = pd.DataFrame(dados)

    if not df_existente.empty:
        df_final = pd.concat([df_existente, df_novo], ignore_index=True)
    else:
        df_final = df_novo

    df_final.to_excel(ARQUIVO_DIARIO, index=False)
    st.success(f"Checklist salvo para o Nº de Série {serie}")

    return df_final, ARQUIVO_DIARIO

def mostrar_resumo():
    if os.path.exists(ARQUIVO_DIARIO):
        df = pd.read_excel(ARQUIVO_DIARIO)

        total_inspecionados = df["Nº Série"].nunique()
        total_aprovado = df[df["Produto Reprovado"] == "Não"]["Nº Série"].nunique()
        total_reprovado = df[df["Produto Reprovado"] == "Sim"]["Nº Série"].nunique()

        percentual_aprov = (total_aprovado / total_inspecionados * 100) if total_inspecionados > 0 else 0

        st.markdown("## 📊 Resumo do Dia")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Inspecionados", total_inspecionados)
        col2.metric("Total Aprovado", total_aprovado)
        col3.metric("Total Reprovado", total_reprovado)
        col4.metric("% Aprovado", f"{percentual_aprov:.1f}%")
    else:
        st.info("Nenhum checklist registrado ainda para hoje.")

def novo_checklist():
    st.markdown("## ✅ Novo Checklist")
    serie = st.text_input("Nº de Série")
    data_atual = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
    st.write(f"Data/Hora: {data_atual}")

    resultados = {}
    foto_etiqueta = None

    for item in itens:
        st.markdown(f"### {item}")
        status = st.radio(f"Status - {item}", ["Conforme", "Não Conforme", "N/A"], key=f"novo_{item}")
        obs = st.text_area(f"Observações - {item}", key=f"obs_novo_{item}")

        if item == "Etiqueta":
            foto_etiqueta = st.camera_input("📸 Tire uma foto da Etiqueta")

        resultados[item] = {"status": status, "obs": obs}

    if st.button("Salvar Checklist"):
        if not serie:
            st.error("Digite o Nº de Série!")
        elif foto_etiqueta is None:
            st.error("⚠️ É obrigatório tirar foto da Etiqueta!")
        else:
            df_final, arquivo = salvar_checklist(serie, resultados, st.session_state['usuario'], foto_etiqueta=foto_etiqueta)

            if df_final is not None:
                # Gerar arquivo para download
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_final.to_excel(writer, index=False)
                output.seek(0)

                nome_arquivo = f"Checklist_{datetime.date.today().strftime('%Y%m%d')}_{serie}.xlsx"

                st.download_button(
                    label="📥 Baixar checklist salvo agora",
                    data=output.getvalue(),
                    file_name=nome_arquivo,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

def reinspecao():
    if os.path.exists(ARQUIVO_DIARIO):
        df = pd.read_excel(ARQUIVO_DIARIO)
        reprovados = df[df["Produto Reprovado"] == "Sim"]["Nº Série"].unique()

        if len(reprovados) > 0:
            st.markdown("## 🔄 Reinspeção de Produtos Reprovados")
            serie_sel = st.selectbox("Selecione o Nº de Série reprovado", reprovados)

            if serie_sel:
                resultados = {}
                for item in itens:
                    st.markdown(f"### {item}")
                    status = st.radio(f"Status - {item} (Reinspeção)", ["Conforme", "Não Conforme", "N/A"], key=f"re_{serie_sel}_{item}")
                    obs = st.text_area(f"Observações - {item}", key=f"re_obs_{serie_sel}_{item}")
                    resultados[item] = {"status": status, "obs": obs}

                if st.button("Salvar Reinspeção"):
                    df_final, _ = salvar_checklist(serie_sel, resultados, st.session_state['usuario'], reinspecao=True)

                    if df_final is not None:
                        output = BytesIO()
                        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                            df_final.to_excel(writer, index=False)
                        output.seek(0)

                        nome_arquivo = f"Reinspecao_{datetime.date.today().strftime('%Y%m%d')}_{serie_sel}.xlsx"

                        st.download_button(
                            label="📥 Baixar reinspeção salva agora",
                            data=output.getvalue(),
                            file_name=nome_arquivo,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
        else:
            st.info("Nenhum produto reprovado para reinspeção.")
    else:
        st.info("Nenhum checklist registrado ainda.")

# --- Streamlit App ---
st.set_page_config(page_title="Checklist de Qualidade", layout="wide")

if 'logged_in' not in st.session_state:
    login()
elif not st.session_state['logged_in']:
    login()
else:
    st.subheader(f"Checklist de Qualidade - Inspetor: {st.session_state['usuario']}")

    # Criar abas
    tab1, tab2, tab3 = st.tabs(["📊 Resumo", "✅ Novo Checklist", "🔄 Reinspeção"])

    with tab1:
        mostrar_resumo()

    with tab2:
        novo_checklist()

    with tab3:
        reinspecao()
