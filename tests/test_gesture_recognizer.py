import pytest
import math
from app.vision.gesture_recognizer import GestureRecognizer, dist_3d

class SyntheticLandmark:
    def __init__(self, x: float, y: float, z: float = 0.0):
        self.x = x
        self.y = y
        self.z = z

def create_synthetic_hand(
    thumb_ext=False,
    index_ext=False,
    middle_ext=False,
    ring_ext=False,
    pinky_ext=False,
    thumb_up=False,
    thumb_down=False,
    pinch=False,
    scale=1.0
):
    """
    Gera 21 landmarks sintéticos para testes determinísticos do GestureRecognizer.
    """
    wx, wy, wz = 0.5, 0.8, 0.0
    lm = [SyntheticLandmark(wx, wy, wz) for _ in range(21)]

    # MCPs das bases dos dedos (tamanho da palma definido pelo MCP médio [9])
    mcp_offsets = {
        1: (-0.05, -0.06), # Thumb CMC
        2: (-0.08, -0.12), # Thumb MCP
        5: (-0.05, -0.22), # Index MCP
        9: (0.00, -0.24),  # Middle MCP (palm_size ~ 0.24)
        13: (0.05, -0.22), # Ring MCP
        17: (0.09, -0.19)  # Pinky MCP
    }
    for idx, (dx, dy) in mcp_offsets.items():
        lm[idx] = SyntheticLandmark(wx + dx * scale, wy + dy * scale, wz)

    # Função auxiliar para gerar articulações (PIP, DIP, TIP) de dedos longos (5..8, 9..12, etc.)
    def set_finger(mcp_idx, is_ext, dx_dir):
        mcp = lm[mcp_idx]
        pip_idx = mcp_idx + 1
        dip_idx = mcp_idx + 2
        tip_idx = mcp_idx + 3

        pip_y = wy - 0.28 * scale
        lm[pip_idx] = SyntheticLandmark(mcp.x + (dx_dir * 0.01) * scale, pip_y, wz)
        lm[dip_idx] = SyntheticLandmark(mcp.x + (dx_dir * 0.015) * scale, wy - 0.35 * scale, wz)

        if is_ext:
            # Estendido: tip bem afastado do wrist
            lm[tip_idx] = SyntheticLandmark(mcp.x + (dx_dir * 0.02) * scale, wy - 0.46 * scale, wz)
        else:
            # Dobrado: tip encolhido próximo ao MCP
            lm[tip_idx] = SyntheticLandmark(mcp.x, wy - 0.15 * scale, wz)

    set_finger(5, index_ext, -1)
    set_finger(9, middle_ext, 0)
    set_finger(13, ring_ext, 1)
    set_finger(17, pinky_ext, 2)

    # Polegar
    t_mcp = lm[2]
    if thumb_up:
        lm[3] = SyntheticLandmark(t_mcp.x, t_mcp.y - 0.08 * scale, wz)
        lm[4] = SyntheticLandmark(t_mcp.x, t_mcp.y - 0.18 * scale, wz)  # tip apontando para cima
    elif thumb_down:
        lm[3] = SyntheticLandmark(t_mcp.x, t_mcp.y + 0.08 * scale, wz)
        lm[4] = SyntheticLandmark(t_mcp.x, t_mcp.y + 0.18 * scale, wz)  # tip apontando para baixo
    elif thumb_ext:
        lm[3] = SyntheticLandmark(t_mcp.x - 0.08 * scale, t_mcp.y - 0.05 * scale, wz)
        lm[4] = SyntheticLandmark(t_mcp.x - 0.16 * scale, t_mcp.y - 0.10 * scale, wz)
    else:
        lm[3] = SyntheticLandmark(t_mcp.x, t_mcp.y - 0.04 * scale, wz)
        lm[4] = SyntheticLandmark(t_mcp.x + 0.04 * scale, t_mcp.y - 0.05 * scale, wz)  # retraído

    if pinch:
        # Coloca o tip do polegar e do indicador muito próximos
        idx_tip = lm[8]
        lm[4] = SyntheticLandmark(idx_tip.x + 0.01 * scale, idx_tip.y + 0.01 * scale, wz)

    return lm

def test_recognizer_all_8_gestures():
    rec = GestureRecognizer()

    # 1. Peace (indicador + médio estendidos, anelar + mínimo dobrados)
    peace_lm = create_synthetic_hand(index_ext=True, middle_ext=True, ring_ext=False, pinky_ext=False)
    g, conf = rec.evaluate_hand(peace_lm)
    assert g == "peace"
    assert conf >= 0.70

    # 2. Open Hand (todos estendidos)
    open_lm = create_synthetic_hand(thumb_ext=True, index_ext=True, middle_ext=True, ring_ext=True, pinky_ext=True)
    g, conf = rec.evaluate_hand(open_lm)
    assert g == "open_hand"
    assert conf >= 0.75

    # 3. Fist (todos dobrados)
    fist_lm = create_synthetic_hand(thumb_ext=False, index_ext=False, middle_ext=False, ring_ext=False, pinky_ext=False)
    g, conf = rec.evaluate_hand(fist_lm)
    assert g == "fist"
    assert conf >= 0.75

    # 4. Point (apenas indicador estendido)
    point_lm = create_synthetic_hand(index_ext=True, middle_ext=False, ring_ext=False, pinky_ext=False)
    g, conf = rec.evaluate_hand(point_lm)
    assert g == "point"
    assert conf >= 0.70

    # 5. Love-you / Rock (indicador + mínimo estendidos, médio + anelar dobrados)
    love_lm = create_synthetic_hand(thumb_ext=True, index_ext=True, middle_ext=False, ring_ext=False, pinky_ext=True)
    g, conf = rec.evaluate_hand(love_lm)
    assert g == "love_you"
    assert conf >= 0.70

    # 6. Thumbs Up (polegar vertical para cima, dedos dobrados)
    t_up_lm = create_synthetic_hand(thumb_up=True, index_ext=False, middle_ext=False, ring_ext=False, pinky_ext=False)
    g, conf = rec.evaluate_hand(t_up_lm)
    assert g == "thumbs_up"
    assert conf >= 0.70

    # 7. Thumbs Down (polegar vertical para baixo, dedos dobrados)
    t_down_lm = create_synthetic_hand(thumb_down=True, index_ext=False, middle_ext=False, ring_ext=False, pinky_ext=False)
    g, conf = rec.evaluate_hand(t_down_lm)
    assert g == "thumbs_down"
    assert conf >= 0.70

    # 8. Pinch (indicador + polegar colados)
    pinch_lm = create_synthetic_hand(pinch=True, index_ext=True, thumb_ext=True)
    g, conf = rec.evaluate_hand(pinch_lm)
    assert g == "pinch"
    assert conf >= 0.65

def test_recognizer_scale_invariance():
    """Testa que uma mão reduzida a 50% do tamanho produz o mesmo gesto e confiança."""
    rec = GestureRecognizer()

    # Peace em escala 1.0 vs escala 0.5
    peace_normal = create_synthetic_hand(index_ext=True, middle_ext=True, ring_ext=False, pinky_ext=False, scale=1.0)
    peace_half = create_synthetic_hand(index_ext=True, middle_ext=True, ring_ext=False, pinky_ext=False, scale=0.5)

    g1, conf1 = rec.evaluate_hand(peace_normal)
    g2, conf2 = rec.evaluate_hand(peace_half)

    assert g1 == g2 == "peace"
    assert abs(conf1 - conf2) < 0.05
