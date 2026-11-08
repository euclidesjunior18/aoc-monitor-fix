#!/usr/bin/env python3
import os
import sys

if "DISPLAY" not in os.environ:
    os.environ["DISPLAY"] = ":0"
if "XAUTHORITY" not in os.environ:
    os.environ["XAUTHORITY"] = os.path.expanduser("~/.Xauthority")

import subprocess
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

AUTOSTART_PATH = os.path.expanduser("~/.config/autostart/aoc-fix-display.desktop")

def get_connected_output():
    try:
        env = os.environ.copy()
        res = subprocess.run(["xrandr"], capture_output=True, text=True, env=env)
        for line in res.stdout.splitlines():
            if " connected" in line and "VGA" in line:
                return line.split()[0]
        for line in res.stdout.splitlines():
            if " connected" in line:
                return line.split()[0]
    except Exception:
        pass
    return "VGA-0"

OUTPUT_NAME = get_connected_output()

# Resoluções principais mais comuns para monitor Full HD / 16:9 / 16:10
COMMON_RESOLUTIONS = [
    ("1920x1080", "1920x1080 (Full HD 16:9 - Padrão)"),
    ("1600x900",  "1600x900 (HD+ 16:9)"),
    ("1368x768",  "1368x768 (WXGA 16:9)"),
    ("1280x720",  "1280x720 (HD 16:9)"),
    ("1680x1050", "1680x1050 (16:10)"),
    ("1440x900",  "1440x900 (16:10)"),
    ("1280x1024", "1280x1024 (5:4)"),
    ("1024x768",  "1024x768 (4:3)")
]

def run_cmd(args):
    try:
        env = os.environ.copy()
        res = subprocess.run(args, capture_output=True, text=True, env=env)
        return res.returncode == 0, res.stdout + res.stderr
    except Exception as e:
        return False, str(e)

class MonitorFixApp(Gtk.Window):
    def __init__(self):
        super().__init__(title="AOC Monitor Control - 24B1W")
        self.set_default_size(500, 540)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_border_width(16)

        self.offset_x = 0
        self.offset_y = 0
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.current_res = "1920x1080"

        # Estados de rollback (segurança de 10s)
        self.previous_res = "1920x1080"
        self.previous_offset_x = 0
        self.previous_offset_y = 0
        self.previous_scale_x = 1.0
        self.countdown_seconds = 10
        self.countdown_timer_id = None
        self.confirm_dialog = None

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.add(main_box)

        # Header Info
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        title_label = Gtk.Label()
        title_label.set_markup("<span size='large' weight='bold'>Controle de Tela AOC 24B1W</span>")
        title_label.set_halign(Gtk.Align.START)
        
        info_label = Gtk.Label()
        info_label.set_markup("<span size='small' color='#666666'>Ajuste manual de deslocamento horizontal/vertical e resolução com reversão de segurança</span>")
        info_label.set_halign(Gtk.Align.START)

        header_box.pack_start(title_label, False, False, 0)
        header_box.pack_start(info_label, False, False, 0)
        main_box.pack_start(header_box, False, False, 0)

        # 1. BOTÃO RESET GERAL (Principal)
        self.btn_reset_all = Gtk.Button()
        reset_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        reset_icon = Gtk.Image.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON)
        reset_text = Gtk.Label()
        reset_text.set_markup("<b>RESETAR TUDO PARA O PADRÃO (Sem Alterações)</b>")
        reset_box.pack_start(reset_icon, False, False, 6)
        reset_box.pack_start(reset_text, False, False, 0)
        reset_box.set_halign(Gtk.Align.CENTER)
        self.btn_reset_all.add(reset_box)
        self.btn_reset_all.set_tooltip_text("Remove qualquer deslocamento, escala ou ajuste e restaura 1920x1080 original.")
        self.btn_reset_all.connect("clicked", self.on_reset_all_clicked)
        main_box.pack_start(self.btn_reset_all, False, False, 0)

        main_box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 0)

        # 2. SELETOR DE RESOLUÇÃO COM CONFIRMAÇÃO DE SEGURANÇA
        res_frame = Gtk.Frame(label=" Resolução da Tela ")
        res_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        res_vbox.set_border_width(10)

        res_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.res_combo = Gtk.ComboBoxText()
        for mode, name in COMMON_RESOLUTIONS:
            self.res_combo.append(mode, name)
        self.res_combo.set_active_id("1920x1080")
        res_hbox.pack_start(self.res_combo, True, True, 0)

        btn_apply_res = Gtk.Button(label="Aplicar Resolução")
        btn_apply_res.connect("clicked", self.on_apply_res_clicked)
        res_hbox.pack_start(btn_apply_res, False, False, 0)

        res_vbox.pack_start(res_hbox, False, False, 0)

        res_tip = Gtk.Label()
        res_tip.set_markup("<span size='small' color='#666666'>Ao mudar de resolução, uma contagem de 10s aparece para reverter se houver problemas de sinal.</span>")
        res_tip.set_halign(Gtk.Align.START)
        res_vbox.pack_start(res_tip, False, False, 0)

        res_frame.add(res_vbox)
        main_box.pack_start(res_frame, False, False, 0)

        # 3. CONTROLE DE POSIÇÃO (MOVER PRO LADO / CIMA / BAIXO)
        pos_frame = Gtk.Frame(label=" Ajuste Manual de Posição (Deslocar Imagem) ")
        pos_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        pos_vbox.set_border_width(10)

        self.pos_status = Gtk.Label()
        self.update_pos_label()
        pos_vbox.pack_start(self.pos_status, False, False, 0)

        grid_pos = Gtk.Grid()
        grid_pos.set_row_spacing(6)
        grid_pos.set_column_spacing(6)
        grid_pos.set_halign(Gtk.Align.CENTER)

        btn_up = Gtk.Button(label="▲ Mover P/ Cima")
        btn_up.connect("clicked", lambda w: self.shift_position(0, 15))
        
        btn_down = Gtk.Button(label="▼ Mover P/ Baixo")
        btn_down.connect("clicked", lambda w: self.shift_position(0, -15))

        btn_left = Gtk.Button(label="◄ Mover P/ Esquerda")
        btn_left.connect("clicked", lambda w: self.shift_position(20, 0))

        btn_right = Gtk.Button(label="Mover P/ Direita ►")
        btn_right.connect("clicked", lambda w: self.shift_position(-20, 0))

        btn_center = Gtk.Button(label="Centralizar (0)")
        btn_center.connect("clicked", self.on_center_clicked)

        grid_pos.attach(btn_up, 1, 0, 1, 1)
        grid_pos.attach(btn_left, 0, 1, 1, 1)
        grid_pos.attach(btn_center, 1, 1, 1, 1)
        grid_pos.attach(btn_right, 2, 1, 1, 1)
        grid_pos.attach(btn_down, 1, 2, 1, 1)

        pos_vbox.pack_start(grid_pos, False, False, 0)

        # Botões de esticar largura (Scale X)
        scale_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        scale_box.set_halign(Gtk.Align.CENTER)
        
        btn_stretch_more = Gtk.Button(label="Esticar Largura (+)")
        btn_stretch_more.set_tooltip_text("Estica a imagem horizontalmente para eliminar barras pretas")
        btn_stretch_more.connect("clicked", lambda w: self.shift_scale(-0.02))

        btn_stretch_less = Gtk.Button(label="Encolher Largura (-)")
        btn_stretch_less.connect("clicked", lambda w: self.shift_scale(0.02))

        btn_stretch_reset = Gtk.Button(label="Largura 100%")
        btn_stretch_reset.connect("clicked", self.on_scale_reset_clicked)

        scale_box.pack_start(btn_stretch_more, False, False, 0)
        scale_box.pack_start(btn_stretch_less, False, False, 0)
        scale_box.pack_start(btn_stretch_reset, False, False, 0)
        pos_vbox.pack_start(scale_box, False, False, 4)

        pos_frame.add(pos_vbox)
        main_box.pack_start(pos_frame, False, False, 0)

        # Autostart Checkbox
        self.chk_autostart = Gtk.CheckButton(label="Salvar e restaurar este ajuste automaticamente ao ligar o PC")
        self.chk_autostart.set_active(os.path.exists(AUTOSTART_PATH))
        self.chk_autostart.connect("toggled", self.on_autostart_toggled)
        main_box.pack_start(self.chk_autostart, False, False, 0)

        # Status feedback label
        self.status_label = Gtk.Label(label="Pronto.")
        self.status_label.set_halign(Gtk.Align.START)
        main_box.pack_start(self.status_label, False, False, 0)

    def update_pos_label(self):
        scale_pct = int((1.0 / self.scale_x) * 100)
        self.pos_status.set_markup(
            f"<small>Deslocamento X: <b>{self.offset_x}px</b> | Y: <b>{self.offset_y}px</b> | Zoom horizontal: <b>{scale_pct}%</b></small>"
        )

    def apply_transform(self):
        tx = float(self.offset_x)
        ty = float(self.offset_y)
        sx = float(self.scale_x)
        sy = float(self.scale_y)
        transform_arg = f"{sx:.4f},0,{tx:.1f},0,{sy:.4f},{ty:.1f},0,0,1"
        ok, out = run_cmd(["xrandr", "--output", OUTPUT_NAME, "--transform", transform_arg])
        self.update_pos_label()
        if self.chk_autostart.get_active():
            self.save_autostart_file()
        return ok, out

    def shift_position(self, dx, dy):
        self.offset_x += dx
        self.offset_y += dy
        ok, out = self.apply_transform()
        if ok:
            self.status_label.set_markup("<span color='#4e9a06'>Posição ajustada!</span>")
        else:
            self.status_label.set_markup(f"<span color='#cc0000'>Erro: {out}</span>")

    def shift_scale(self, ds):
        self.scale_x = max(0.7, min(1.3, self.scale_x + ds))
        ok, out = self.apply_transform()
        if ok:
            self.status_label.set_markup("<span color='#4e9a06'>Largura ajustada!</span>")
        else:
            self.status_label.set_markup(f"<span color='#cc0000'>Erro: {out}</span>")

    def on_center_clicked(self, widget):
        self.offset_x = 0
        self.offset_y = 0
        ok, out = self.apply_transform()
        if ok:
            self.status_label.set_markup("<span color='#4e9a06'>Posição centralizada.</span>")

    def on_scale_reset_clicked(self, widget):
        self.scale_x = 1.0
        self.scale_y = 1.0
        ok, out = self.apply_transform()
        if ok:
            self.status_label.set_markup("<span color='#4e9a06'>Largura restaurada para 100%.</span>")

    def on_apply_res_clicked(self, widget):
        target_mode = self.res_combo.get_active_id()
        if not target_mode or target_mode == self.current_res:
            return

        # Guarda estado anterior completo para rollback
        self.previous_res = self.current_res
        self.previous_offset_x = self.offset_x
        self.previous_offset_y = self.offset_y
        self.previous_scale_x = self.scale_x

        self.status_label.set_markup(f"<span color='#3465a4'>Testando resolução {target_mode}...</span>")
        ok, out = run_cmd(["xrandr", "--output", OUTPUT_NAME, "--mode", target_mode])
        if not ok:
            self.status_label.set_markup(f"<span color='#cc0000'>Falha ao alterar resolução: {out}</span>")
            return

        self.current_res = target_mode
        self.apply_transform()
        self.start_confirmation_dialog(target_mode)

    def start_confirmation_dialog(self, mode):
        self.countdown_seconds = 10

        self.confirm_dialog = Gtk.Dialog(
            title="Confirmar Resolução",
            parent=self,
            flags=Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT
        )
        self.confirm_dialog.set_default_size(360, 160)
        self.confirm_dialog.set_border_width(12)

        content = self.confirm_dialog.get_content_area()
        self.lbl_dialog_text = Gtk.Label()
        self.lbl_dialog_text.set_markup(
            f"<b>Deseja manter a resolução {mode}?</b>\n\n"
            f"Revertendo automaticamente em <b>{self.countdown_seconds}</b> segundos se não confirmar..."
        )
        self.lbl_dialog_text.set_justify(Gtk.Justification.CENTER)
        content.pack_start(self.lbl_dialog_text, True, True, 10)

        # Botão Reverter
        btn_revert = self.confirm_dialog.add_button("Reverter Agora", Gtk.ResponseType.CANCEL)
        # Botão Manter
        btn_keep = self.confirm_dialog.add_button("Manter Resolução", Gtk.ResponseType.OK)
        btn_keep.get_style_context().add_class("suggested-action")

        self.confirm_dialog.show_all()

        # Inicia temporizador de 1 segundo
        if self.countdown_timer_id:
            GLib.source_remove(self.countdown_timer_id)
        self.countdown_timer_id = GLib.timeout_add(1000, self.on_countdown_tick)

        response = self.confirm_dialog.run()
        self.handle_dialog_response(response)

    def on_countdown_tick(self):
        self.countdown_seconds -= 1
        if self.countdown_seconds <= 0:
            # Tempo esgotado: fecha o diálogo e reverte
            if self.confirm_dialog:
                self.confirm_dialog.response(Gtk.ResponseType.CANCEL)
            return False

        if self.lbl_dialog_text:
            self.lbl_dialog_text.set_markup(
                f"<b>Deseja manter a resolução {self.current_res}?</b>\n\n"
                f"Revertendo automaticamente em <b>{self.countdown_seconds}</b> segundos se não confirmar..."
            )
        return True

    def handle_dialog_response(self, response):
        if self.countdown_timer_id:
            GLib.source_remove(self.countdown_timer_id)
            self.countdown_timer_id = None

        if self.confirm_dialog:
            self.confirm_dialog.destroy()
            self.confirm_dialog = None

        if response == Gtk.ResponseType.OK:
            # Usuário confirmou
            self.status_label.set_markup(f"<span color='#4e9a06'>✓ Resolução {self.current_res} confirmada e mantida!</span>")
            if self.chk_autostart.get_active():
                self.save_autostart_file()
        else:
            # Reversão automática ou cancelado
            self.revert_previous_settings()

    def revert_previous_settings(self):
        self.status_label.set_markup(f"<span color='#ce5c00'>Revertendo para a resolução anterior ({self.previous_res})...</span>")
        run_cmd(["xrandr", "--output", OUTPUT_NAME, "--mode", self.previous_res])
        self.current_res = self.previous_res
        self.offset_x = self.previous_offset_x
        self.offset_y = self.previous_offset_y
        self.scale_x = self.previous_scale_x
        self.res_combo.set_active_id(self.current_res)
        self.apply_transform()
        self.status_label.set_markup(f"<span color='#3465a4'>Configuração anterior restaurada com sucesso.</span>")

    def on_reset_all_clicked(self, widget):
        self.status_label.set_markup("<span color='#3465a4'>Resetando para o padrão original...</span>")
        self.offset_x = 0
        self.offset_y = 0
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.res_combo.set_active_id("1920x1080")
        self.current_res = "1920x1080"
        
        # 1. Reset transform
        run_cmd(["xrandr", "--output", OUTPUT_NAME, "--transform", "none"])
        # 2. Reset scaling mode
        run_cmd(["xrandr", "--output", OUTPUT_NAME, "--set", "scaling mode", "None"])
        # 3. Auto padrão
        ok, out = run_cmd(["xrandr", "--output", OUTPUT_NAME, "--auto", "--mode", "1920x1080", "--rate", "60.00"])
        
        self.update_pos_label()
        if ok:
            self.status_label.set_markup("<span color='#4e9a06'>✓ Monitor resetado para as definições de fábrica!</span>")
        else:
            self.status_label.set_markup(f"<span color='#cc0000'>Erro: {out}</span>")

    def save_autostart_file(self):
        cmd = f"/home/junior/.local/bin/aoc-monitor-fix --apply-custom {self.current_res} {self.offset_x} {self.offset_y} {self.scale_x:.4f}"
        content = f"""[Desktop Entry]
Type=Application
Exec={cmd}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=AOC Monitor Fix Autostart
Comment=Restaura proporcao e ajuste do monitor AOC
"""
        try:
            with open(AUTOSTART_PATH, "w") as f:
                f.write(content)
        except Exception as e:
            print("Erro ao gravar autostart:", e)

    def on_autostart_toggled(self, widget):
        if widget.get_active():
            self.save_autostart_file()
            self.status_label.set_text("Ajustes salvos para iniciar automaticamente com o sistema.")
        else:
            if os.path.exists(AUTOSTART_PATH):
                try:
                    os.remove(AUTOSTART_PATH)
                    self.status_label.set_text("Início automático desativado.")
                except Exception as e:
                    self.status_label.set_text(f"Erro ao remover autostart: {e}")

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--apply-custom":
        import time
        time.sleep(2)
        try:
            mode = sys.argv[2]
            ox = float(sys.argv[3])
            oy = float(sys.argv[4])
            sx = float(sys.argv[5])
            run_cmd(["xrandr", "--output", OUTPUT_NAME, "--mode", mode])
            t_arg = f"{sx:.4f},0,{ox:.1f},0,1.0000,{oy:.1f},0,0,1"
            run_cmd(["xrandr", "--output", OUTPUT_NAME, "--transform", t_arg])
        except Exception as e:
            pass
        sys.exit(0)
    elif len(sys.argv) > 1 and sys.argv[1] == "--reset":
        run_cmd(["xrandr", "--output", OUTPUT_NAME, "--transform", "none"])
        run_cmd(["xrandr", "--output", OUTPUT_NAME, "--set", "scaling mode", "None"])
        run_cmd(["xrandr", "--output", OUTPUT_NAME, "--auto", "--mode", "1920x1080", "--rate", "60.00"])
        sys.exit(0)

    app = MonitorFixApp()
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()
