# 🖐️ OBS Gesture Control V2.0

O **OBS Gesture Control V2** é um sistema completo e moderno de controle por gestos para o **OBS Studio**, permitindo trocar cenas, ativar/desativar fontes, controlar áudio, iniciar/pausar gravações e transmissões usando apenas gestos das mãos em frente à webcam.

Toda a configuração é realizada através da **interface gráfica**, sem a necessidade de editar nenhum código Python ou arquivo JSON.

---

## 🚀 Funcionalidades Principais

* **8 Gestos Pré-definidos e Estáveis:**
  1. ✌️ **Peace (Paz)**
  2. 👍 **Thumbs Up (Positivo)**
  3. 👎 **Thumbs Down (Negativo)**
  4. 🖐️ **Open Hand (Mão Aberta)**
  5. ✊ **Fist (Punho Fechado)**
  6. ☝️ **Point (Apontar)**
  7. 🤟 **Love-You (Rock)**
  8. 🤏 **Pinch (Pinça)**
* **Descoberta Automática do OBS:** Conecta via WebSocket 5.x e lista automaticamente suas cenas e fontes nos menus da interface.
* **16 Ações Configuráveis + Comando Personalizado (SO).**
* **Sistema de Perfis Ilimitados:** Crie perfis para *Live Gaming*, *Just Chatting*, *Gravação*, *YouTube*, etc.
* **Detecção Inteligente & Anti-Oscilação:** Suporte a janela de N frames de confirmação, filtro de estabilidade, cooldown e prioridade de gestos para evitar disparos acidentais.
* **Ferramenta de Calibração Interativa:** Avalia a iluminação e estabilidade visual em tempo real.
* **Rastreamento de Mãos & Mão Preferida:** Rastreamento em tempo real 100% local com **Google MediaPipe Tasks**, com suporte à escolha de mão preferida (qualquer, esquerda ou direita).

---

## 📦 Guia de Instalação e Uso Passo a Passo

### 1. Requisitos Prévios
* **Sistema Operacional:** Windows 10 ou Windows 11.
* **Python:** Versão 3.10, 3.11 ou 3.12 instalada.
* **OBS Studio:** Versão 28.0 ou superior (com WebSocket 5.x integrado).
* **Webcam:** Qualquer webcam USB ou aplicativo de câmera virtual (Iriun, DroidCam, etc.).

---

### 2. Ativação do OBS WebSocket
1. Abra o **OBS Studio**.
2. Acesse o menu **Ferramentas** -> **Configurações do Servidor WebSocket**.
3. Marque a opção **Ativar Servidor WebSocket**.
4. Anote a **Porta do Servidor** (padrão: `4455`) e defina sua **Senha de Autenticação** (ou desative a autenticação caso prefira conexão sem senha).

---

### 3. Instalação e Execução

#### Opção A: Execução Automática (Recomendado)
Basta dar dois cliques no arquivo **`run.bat`**. Ele irá:
1. Criar o ambiente virtual `.venv` automaticamente.
2. Instalar todas as dependências do `requirements.txt`.
3. Iniciar a interface gráfica do programa.

#### Opção B: Via Terminal / Prompt de Comando
```bash
# 1. Abrir a pasta do projeto no terminal
cd obs-gesture-control

# 2. Criar ambiente virtual
python -m venv .venv

# 3. Ativar o ambiente virtual no Windows
.venv\Scripts\activate

# 4. Instalar as dependências
pip install -r requirements.txt

# 5. Iniciar o aplicativo
python main.py
```

---

## 🎮 Como Usar o Sistema

1. **Conectar ao OBS:**
   * Abra a aba **🎥 OBS Studio** na interface.
   * Digite a porta (`4455`) e a senha configurada no OBS.
   * Clique em **⚡ Conectar Agora**. As cenas e fontes serão descobertas automaticamente!
2. **Ativar Modo Teste (Recomendado na Primeira Vez):**
   * No topo do **Dashboard**, ative o botão **[ MODO TESTE ]**.
   * Faça o gesto ✌️ diante da câmera e veja a ação simulada no painel sem afetar sua transmissão.
3. **Personalizar Gestos:**
   * Na aba **✌️ Gestos**, clique no botão **Editar** de qualquer um dos 8 gestos.
   * Escolha a Ação (Trocar cena, Ativar fonte, etc.) e selecione a Cena/Fonte desejada no menu suspenso.
   * Ajuste o **Cooldown** e os **Frames de Confirmação** se desejar.
   * Clique em **💾 Salvar Alterações**.
4. **Gerenciar Perfis:**
   * Na aba **👤 Perfis**, você pode criar novos perfis para transmissões diferentes (ex: *Live Gaming*, *Gravação*) e alternar entre eles em um clique.

---

## 🔧 Solução de Problemas

* **A câmera fica preta ou não abre:**
  * Vá para a aba **📷 Câmera** e altere o índice do dispositivo para `1`, `2` ou `0`.
  * Verifique se outro programa (Discord, Zoom, Chrome) não está ocupando a câmera exclusivamente.
* **O OBS não conecta:**
  * Verifique se o OBS Studio está aberto.
  * Confirme se a opção **Ativar Servidor WebSocket** está marcada em `Ferramentas -> Configurações do Servidor WebSocket`.
  * Verifique se a senha informada na aba **OBS** da interface corresponde exatamente à senha do OBS.
* **Gesto oscila ou não reconhece:**
  * Use a aba **🎯 Calibração** para testar a qualidade visual.
  * Garanta uma boa iluminação frontal e contraste entre sua mão e o fundo.

---

## 🛡️ Privacidade e Segurança Local
* O processamento de imagem roda **100% LOCALMENTE** em seu computador usando o Google MediaPipe.
* Nenhuma imagem da webcam ou dado é enviado para a nuvem ou servidores externos.
