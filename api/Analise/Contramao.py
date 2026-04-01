import cv2
import numpy as np
from ultralytics import YOLO
from collections import defaultdict, deque
import math
import time
from datetime import datetime
import os

# ============================================
# PARTE 1: DETETOR DE CONTRAMÃO
# ============================================

class DetetorContramao:
    """
    Deteta veículos em contramão
    """
    def __init__(self, fps=30):
        self.sentido_via = 'direita'
        self.min_frames_para_alerta = 5
        self.historico_contramao = defaultdict(list)
        self.alertas_enviados = set()
        self.fps = fps
        self.tempo_min_infracao = 1
        self.ultimo_debug = {}
        
    def definir_sentido_via(self, sentido):
        self.sentido_via = sentido
        sentido_texto = "→ DIREITA" if sentido == 'direita' else "← ESQUERDA"
        print(f" Sentido da via definido: {sentido_texto}")
        
    def calcular_direcao_veiculo(self, centros):
        if len(centros) < 5:
            return 'desconhecida'
        
        dx_total = 0
        movimentos_validos = 0
        
        for i in range(1, min(6, len(centros))):
            x_ant, y_ant = centros[-i-1]
            x_nov, y_nov = centros[-i]
            dx = x_nov - x_ant
            
            if abs(dx) > 5:
                dx_total += dx
                movimentos_validos += 1
        
        if movimentos_validos == 0:
            movimentos_pequenos = 0
            for i in range(1, min(10, len(centros))):
                x_ant, y_ant = centros[-i-1]
                x_nov, y_nov = centros[-i]
                dx = x_nov - x_ant
                if abs(dx) < 5:
                    movimentos_pequenos += 1
            
            if movimentos_pequenos >= 5:
                return 'parado'
            return 'desconhecida'
        
        dx_medio = dx_total / movimentos_validos
        
        if dx_medio > 8:
            return 'direita'
        elif dx_medio < -8:
            return 'esquerda'
        else:
            return 'parado'
    
    def detetar(self, veiculo_id, dados, frame_num):
        if not dados['centros'] or len(dados['centros']) < 5:
            return False, "dados insuficientes", 0
        
        direcao = self.calcular_direcao_veiculo(dados['centros'])
        
        if direcao == 'desconhecida' or direcao == 'parado':
            if veiculo_id in self.historico_contramao and self.historico_contramao[veiculo_id]:
                self.historico_contramao[veiculo_id] = []
            return False, "direção indeterminada", 0
        
        esta_contramao = False
        motivo = ""
        
        if self.sentido_via == 'direita' and direcao == 'esquerda':
            esta_contramao = True
            motivo = f"Indo para ESQUERDA (via sentido DIREITA)"
        elif self.sentido_via == 'esquerda' and direcao == 'direita':
            esta_contramao = True
            motivo = f"Indo para DIREITA (via sentido ESQUERDA)"
        
        if esta_contramao:
            self.historico_contramao[veiculo_id].append(frame_num)
            
            if len(self.historico_contramao[veiculo_id]) > 60:
                self.historico_contramao[veiculo_id].pop(0)
            
            frames_consecutivos = self._contar_frames_consecutivos(self.historico_contramao[veiculo_id])
            tempo_infracao = frames_consecutivos / self.fps
            
            if frames_consecutivos >= self.min_frames_para_alerta:
                return True, motivo, tempo_infracao
            else:
                return False, f"verificando ({frames_consecutivos}/{self.min_frames_para_alerta})", tempo_infracao
        else:
            if veiculo_id in self.historico_contramao and self.historico_contramao[veiculo_id]:
                self.historico_contramao[veiculo_id] = []
            return False, "direção correta", 0
    
    def _contar_frames_consecutivos(self, frames):
        if not frames:
            return 0
        
        frames_ordenados = sorted(frames)
        consecutivos = 1
        max_consecutivos = 1
        
        for i in range(1, len(frames_ordenados)):
            if frames_ordenados[i] == frames_ordenados[i-1] + 1:
                consecutivos += 1
                max_consecutivos = max(max_consecutivos, consecutivos)
            else:
                consecutivos = 1
        
        return max_consecutivos
    
    def get_veiculos_contramao(self):
        em_contramao = []
        for vid, hist in self.historico_contramao.items():
            if self._contar_frames_consecutivos(hist) >= self.min_frames_para_alerta:
                em_contramao.append(vid)
        return em_contramao
    
    def registrar_alerta(self, veiculo_id, frame_num, screenshot_path=None):
        self.alertas_enviados.add(veiculo_id)
        print(f"\n ALERTA ENVIADO! Veículo {veiculo_id} em contramão no frame {frame_num}")
        if screenshot_path:
            print(f"   📸 Screenshot: {screenshot_path}")


# ============================================
# PARTE 2: RASTREADOR DE VEÍCULOS
# ============================================

class RastreadorVeiculos:
    def __init__(self, max_historico=50):
        self.veiculos = {}
        self.proximo_id = 0
        self.cores = {}
        self.max_historico = max_historico
        self.distancia_maxima = 100
        
    def atualizar(self, detecoes, frame_num):
        veiculos_atuais = []
        detecoes_associadas = set()
        
        for veiculo_id, dados in self.veiculos.items():
            ultimo_centro = dados['ultimo_centro']
            melhor_dist = float('inf')
            melhor_det = None
            melhor_idx = -1
            
            for idx, det in enumerate(detecoes):
                if idx in detecoes_associadas:
                    continue
                    
                centro = det['centro']
                dist = math.sqrt((ultimo_centro[0] - centro[0])**2 + 
                                (ultimo_centro[1] - centro[1])**2)
                
                if dist < melhor_dist and dist < self.distancia_maxima:
                    melhor_dist = dist
                    melhor_det = det
                    melhor_idx = idx
            
            if melhor_det:
                centro = melhor_det['centro']
                dados['centros'].append(centro)
                dados['ultimo_centro'] = centro
                dados['ultimo_frame'] = frame_num
                dados['classe'] = melhor_det['classe']
                dados['bbox'] = melhor_det['bbox']
                
                veiculos_atuais.append(veiculo_id)
                detecoes_associadas.add(melhor_idx)
        
        for idx, det in enumerate(detecoes):
            if idx not in detecoes_associadas:
                novo_id = self.proximo_id
                self.proximo_id += 1
                
                self.veiculos[novo_id] = {
                    'centros': deque([det['centro']], maxlen=self.max_historico),
                    'ultimo_centro': det['centro'],
                    'ultimo_frame': frame_num,
                    'primeiro_frame': frame_num,
                    'classe': det['classe'],
                    'bbox': det['bbox']
                }
                
                self.cores[novo_id] = (
                    np.random.randint(50, 255),
                    np.random.randint(50, 255),
                    np.random.randint(50, 255)
                )
                
                veiculos_atuais.append(novo_id)
        
        ids_remover = []
        for veiculo_id, dados in self.veiculos.items():
            if frame_num - dados['ultimo_frame'] > 60:
                ids_remover.append(veiculo_id)
        
        for vid in ids_remover:
            del self.veiculos[vid]
        
        return veiculos_atuais
    
    def get_dados_veiculo(self, veiculo_id):
        return self.veiculos.get(veiculo_id)


# ============================================
# PARTE 3: DETETOR DE FAIXAS
# ============================================

class DetetorFaixas:
    def __init__(self):
        self.faixa_esquerda = None
        self.faixa_direita = None
        self.centro_via = None
        
    def processar(self, frame):
        altura, largura = frame.shape[:2]
        
        cinza = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(cinza, (5, 5), 0)
        bordas = cv2.Canny(blur, 50, 150)
        
        mascara = np.zeros_like(bordas)
        vertices = np.array([[
            (0, altura),
            (largura * 0.4, altura * 0.6),
            (largura * 0.6, altura * 0.6),
            (largura, altura)
        ]], dtype=np.int32)
        cv2.fillPoly(mascara, vertices, 255)
        roi = cv2.bitwise_and(bordas, mascara)
        
        linhas = cv2.HoughLinesP(roi, rho=1, theta=np.pi/180, 
                                 threshold=50, minLineLength=50, maxLineGap=150)
        
        linhas_esq = []
        linhas_dir = []
        
        if linhas is not None:
            for linha in linhas:
                x1, y1, x2, y2 = linha[0]
                if x2 - x1 == 0:
                    continue
                inclinacao = (y2 - y1) / (x2 - x1)
                
                if inclinacao < -0.3:
                    linhas_esq.append(linha[0])
                elif inclinacao > 0.3:
                    linhas_dir.append(linha[0])
        
        if linhas_esq:
            self.faixa_esquerda = self._linha_media(linhas_esq, altura)
        if linhas_dir:
            self.faixa_direita = self._linha_media(linhas_dir, altura)
        
        if self.faixa_esquerda and self.faixa_direita:
            x1_esq, _, x2_esq, _ = self.faixa_esquerda
            x1_dir, _, x2_dir, _ = self.faixa_direita
            centro_esq = (x1_esq + x2_esq) // 2
            centro_dir = (x1_dir + x2_dir) // 2
            self.centro_via = (centro_esq + centro_dir) // 2
        
        return self.faixa_esquerda, self.faixa_direita, self.centro_via
    
    def _linha_media(self, linhas, altura):
        pontos_x = []
        pontos_y = []
        
        for linha in linhas:
            x1, y1, x2, y2 = linha
            pontos_x.extend([x1, x2])
            pontos_y.extend([y1, y2])
        
        if len(pontos_x) > 1:
            coeficientes = np.polyfit(pontos_y, pontos_x, 1)
            y1 = altura
            y2 = int(altura * 0.6)
            x1 = int(coeficientes[0] * y1 + coeficientes[1])
            x2 = int(coeficientes[0] * y2 + coeficientes[1])
            return (x1, y1, x2, y2)
        return None
    
    def desenhar_faixas(self, frame):
        frame_anotado = frame.copy()
        
        if self.faixa_esquerda:
            x1, y1, x2, y2 = self.faixa_esquerda
            cv2.line(frame_anotado, (x1, y1), (x2, y2), (0, 255, 0), 3)
        
        if self.faixa_direita:
            x1, y1, x2, y2 = self.faixa_direita
            cv2.line(frame_anotado, (x1, y1), (x2, y2), (0, 255, 0), 3)
        
        if self.centro_via:
            cv2.line(frame_anotado, (self.centro_via, 0), 
                    (self.centro_via, frame.shape[0]), (255, 255, 0), 2)
        
        return frame_anotado


# ============================================
# PARTE 4: PROCESSAMENTO PRINCIPAL COM SALVAMENTO DE VÍDEO
# ============================================

def processar_video_contramao(caminho_video=None, salvar_video=True):
    """
    Processa vídeo detetando veículos em contramão e SALVA o vídeo processado
    """
    print("\n" + "="*60)
    print(" DETEÇÃO DE CONTRAMÃO COM SALVAMENTO DE VÍDEO")
    print("="*60)
    
    # Carregar modelo
    modelo = YOLO('yolov8n.pt')
    
    # Abrir vídeo de entrada
    if caminho_video:
        cap = cv2.VideoCapture(caminho_video)
        print(f" Vídeo de entrada: {caminho_video}")
    else:
        cap = cv2.VideoCapture(0)
        print(" Webcam")
    
    if not cap.isOpened():
        print(" Erro ao abrir vídeo!")
        return
    
    # Obter informações do vídeo
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30
    
    largura = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    altura = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f" FPS: {fps:.1f}")
    print(f" Resolução: {largura}x{altura}")
    
    # Criar diretório para saída
    output_dir = "videos_processados"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Nome do vídeo de saída
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    if caminho_video:
        nome_base = os.path.splitext(os.path.basename(caminho_video))[0]
        output_path = f"{output_dir}/{nome_base}_analise_contramao_{timestamp}.mp4"
    else:
        output_path = f"{output_dir}/webcam_analise_contramao_{timestamp}.mp4"
    
    # Configurar writer de vídeo
    if salvar_video:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (largura, altura))
        print(f" Vídeo de saída: {output_path}")
    
    # Inicializar componentes
    rastreador = RastreadorVeiculos(max_historico=50)
    faixas = DetetorFaixas()
    detetor_contramao = DetetorContramao(fps=fps)
    
    # Perguntar sentido da via
    print("\n" + "="*60)
    print("  CONFIGURAÇÃO DO SENTIDO DA VIA")
    print("="*60)
    print("   1 - DIREITA → (veículos devem ir para a DIREITA)")
    print("   2 - ESQUERDA ← (veículos devem ir para a ESQUERDA)")
    print("-"*60)
    
    sentido_opcao = input("   Opção (1 ou 2): ").strip()
    
    if sentido_opcao == '1':
        detetor_contramao.definir_sentido_via('direita')
    else:
        detetor_contramao.definir_sentido_via('esquerda')
    
    # Configurações
    frame_count = 0
    start_time = time.time()
    
    # Log
    log_file = open(f"{output_dir}/contramao_log_{timestamp}.csv", "w")
    log_file.write("timestamp,frame,id,x,y,classe,direcao,em_contramao,tempo_infracao\n")
    
    print("\n PROCESSANDO... Comandos:")
    print("   'q' - sair e salvar vídeo")
    print("   's' - guardar screenshot")
    print("   'd' - mostrar estatísticas")
    print("   'c' - mostrar veículos em contramão")
    print("-"*50)
    print(f" O vídeo está sendo salvo em: {output_path}")
    print("-"*50)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        timestamp_str = datetime.now().strftime('%H:%M:%S')
        
        # Reduzir resolução para melhor performance (apenas para deteção)
        frame_pequeno = cv2.resize(frame, (640, 360))
        escala_x = frame.shape[1] / 640
        escala_y = frame.shape[0] / 360
        
        # Detetar faixas (opcional)
        faixa_esq, faixa_dir, centro_via = faixas.processar(frame)
        
        # Detetar veículos
        resultados = modelo(frame_pequeno, classes=[2, 3, 5, 7])
        
        # Extrair deteções
        detecoes = []
        for det in resultados[0]:
            x1, y1, x2, y2 = det.boxes.xyxy[0].cpu().numpy().astype(int)
            classe_id = int(det.boxes.cls[0].cpu().numpy())
            confianca = float(det.boxes.conf[0].cpu().numpy())
            
            x1 = int(x1 * escala_x)
            y1 = int(y1 * escala_y)
            x2 = int(x2 * escala_x)
            y2 = int(y2 * escala_y)
            
            centro_x = (x1 + x2) // 2
            centro_y = (y1 + y2) // 2
            
            nome_classes = {2: 'carro', 3: 'moto', 5: 'autocarro', 7: 'camiao'}
            classe = nome_classes.get(classe_id, 'desconhecido')
            
            detecoes.append({
                'centro': (centro_x, centro_y),
                'bbox': (x1, y1, x2, y2),
                'classe': classe,
                'confianca': confianca
            })
        
        # Atualizar tracking
        veiculos_ativos = rastreador.atualizar(detecoes, frame_count)
        
        # Desenhar
        frame_anotado = frame.copy()
        frame_anotado = faixas.desenhar_faixas(frame_anotado)
        
        # Desenhar seta de sentido da via
        if detetor_contramao.sentido_via == 'direita':
            seta_inicio = (frame.shape[1] - 100, 50)
            seta_fim = (frame.shape[1] - 30, 50)
            cv2.arrowedLine(frame_anotado, seta_inicio, seta_fim, (0, 255, 0), 3)
            cv2.putText(frame_anotado, "SENTIDO PERMITIDO", (frame.shape[1] - 250, 40),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        else:
            seta_inicio = (30, 50)
            seta_fim = (100, 50)
            cv2.arrowedLine(frame_anotado, seta_fim, seta_inicio, (0, 255, 0), 3)
            cv2.putText(frame_anotado, "SENTIDO PERMITIDO", (10, 40),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # Processar veículos
        veiculos_contramao = []
        
        for veiculo_id in veiculos_ativos:
            dados = rastreador.get_dados_veiculo(veiculo_id)
            if not dados:
                continue
            
            cor = rastreador.cores[veiculo_id]
            ultimo_centro = dados['ultimo_centro']
            x1, y1, x2, y2 = dados['bbox']
            
            # Detetar contramão
            direcao = detetor_contramao.calcular_direcao_veiculo(dados['centros'])
            em_contramao, motivo, tempo_infracao = detetor_contramao.detetar(
                veiculo_id, dados, frame_count
            )
            
            if em_contramao:
                veiculos_contramao.append(veiculo_id)
                
                # Guardar evidência (screenshot) a cada infração
                if veiculo_id not in detetor_contramao.alertas_enviados:
                    screenshot_path = f"{output_dir}/contramao_id{veiculo_id}_frame{frame_count}.jpg"
                    cv2.imwrite(screenshot_path, frame)
                    detetor_contramao.registrar_alerta(veiculo_id, frame_count, screenshot_path)
            
            # Guardar log
            log_file.write(f"{timestamp_str},{frame_count},{veiculo_id},"
                          f"{ultimo_centro[0]},{ultimo_centro[1]},{dados['classe']},"
                          f"{direcao},{1 if em_contramao else 0},{tempo_infracao:.1f}\n")
            
            # Desenhar bounding box
            if em_contramao:
                # VERMELHO para contramão
                cv2.rectangle(frame_anotado, (x1, y1), (x2, y2), (0, 0, 255), 3)
                
                # Fundo vermelho para o alerta
                cv2.rectangle(frame_anotado, (x1, y2+5), (x1+220, y2+45), 
                             (0, 0, 255), -1)
                cv2.putText(frame_anotado, " CONTRAMAO!", (x1+5, y2+32),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
                # Mostrar tempo de infração
                if tempo_infracao > 0:
                    cv2.putText(frame_anotado, f"{tempo_infracao:.1f}s", 
                               (x1, y2+65), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            else:
                cv2.rectangle(frame_anotado, (x1, y1), (x2, y2), cor, 2)
            
            # Desenhar ID e direção
            cv2.putText(frame_anotado, f"ID:{veiculo_id}", (x1, y1-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, cor, 2)
            
            # Mostrar direção com seta
            if direcao == 'direita':
                cv2.putText(frame_anotado, "→", (x1+5, y1-30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            elif direcao == 'esquerda':
                cv2.putText(frame_anotado, "←", (x1+5, y1-30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            
            # Desenhar centro
            cv2.circle(frame_anotado, ultimo_centro, 4, (0, 0, 255), -1)
            
            # Desenhar trajetória
            centros = list(dados['centros'])
            if len(centros) > 1:
                for i in range(1, len(centros)):
                    intensidade = max(50, 255 - (len(centros) - i) * 15)
                    cor_traco = (int(cor[0] * intensidade/255),
                                int(cor[1] * intensidade/255),
                                int(cor[2] * intensidade/255))
                    cv2.line(frame_anotado, centros[i-1], centros[i], cor_traco, 2)
        
        # Informações no ecrã
        fps_atual = frame_count / (time.time() - start_time)
        
        cv2.putText(frame_anotado, f"Frame: {frame_count}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame_anotado, f"Veiculos: {len(veiculos_ativos)}", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame_anotado, f"Contramao: {len(veiculos_contramao)}", (10, 90),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.putText(frame_anotado, f"FPS: {fps_atual:.1f}", (10, 120),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # Instruções
        cv2.putText(frame_anotado, "q-sair | s-screenshot | d-stats | c-contramao", 
                   (10, frame.shape[0]-20), cv2.FONT_HERSHEY_SIMPLEX, 
                   0.5, (255, 255, 255), 1)
        
        # Adicionar marca d'água de análise
        cv2.putText(frame_anotado, f"Analise Contramao - {timestamp}", 
                   (frame.shape[1]-250, frame.shape[0]-10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Mostrar
        cv2.imshow('Deteccao de Contramao - Modulo 7', frame_anotado)
        
        # SALVAR FRAME NO VÍDEO
        if salvar_video:
            out.write(frame_anotado)
        
        # Comandos
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            screenshot_path = f"{output_dir}/screenshot_frame_{frame_count}.jpg"
            cv2.imwrite(screenshot_path, frame_anotado)
            print(f" Screenshot: {screenshot_path}")
        elif key == ord('d'):
            print(f"\n ESTATÍSTICAS:")
            print(f"   Frames: {frame_count}")
            print(f"   FPS: {fps_atual:.1f}")
            print(f"   Veículos únicos: {rastreador.proximo_id}")
            print(f"   Veículos em contramão: {len(veiculos_contramao)}")
            print(f"   Alertas enviados: {len(detetor_contramao.alertas_enviados)}")
        elif key == ord('c'):
            veiculos_cm = detetor_contramao.get_veiculos_contramao()
            print(f"\n  VEÍCULOS EM CONTRAMÃO ({len(veiculos_cm)}):")
            if veiculos_cm:
                for vid in veiculos_cm:
                    dados = rastreador.get_dados_veiculo(vid)
                    if dados:
                        direcao = detetor_contramao.calcular_direcao_veiculo(dados['centros'])
                        print(f"   ID:{vid} - direção: {direcao} - pos: {dados['ultimo_centro']}")
            else:
                print("   Nenhum veículo em contramão")
    
    # Fechar recursos
    cap.release()
    if salvar_video:
        out.release()
    cv2.destroyAllWindows()
    log_file.close()
    
    print(f"\n Processamento concluído!")
    print(f" Pasta de saída: {output_dir}")
    if salvar_video:
        print(f" Vídeo processado: {output_path}")
    print(f" Log: {output_dir}/contramao_log_{timestamp}.csv")
    print(f" Veículos únicos: {rastreador.proximo_id}")
    print(f"  Alertas de contramão: {len(detetor_contramao.alertas_enviados)}")





# ============================================
# PARTE 6: FUNÇÃO PRINCIPAL
# ============================================

def main_contramao(caminho=None):
    """
    Função principal com menu
    """
    processar_video_contramao(caminho, salvar_video=True)