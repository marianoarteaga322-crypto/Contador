import flet as ft
import sqlite3
import datetime
import os

def main(page: ft.Page):
    page.title = "ConFin"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#0B0E17"
    page.padding = 0
    page.window_full_screen = True

    # Paleta Premium
    C_BG = "#0B0E17"
    C_CARD = "#151B2B"
    C_BLUE = "#3B82F6"
    C_PURPLE = "#8B5CF6"
    C_GREEN = "#10B981"
    C_RED = "#EF4444"
    C_ORANGE = "#F59E0B"
    C_TEXT_MAIN = "#F8FAFC"
    C_TEXT_SEC = "#64748B"

    # --- RUTA DE BASE DE DATOS PERMANENTE EN ANDROID ---
    pkg_path = "/data/user/0/com.mariano.ConFin/files"
    pkg_path_alt = "/data/data/com.mariano.ConFin/files"
    
    if os.path.exists(pkg_path):
        db_path = os.path.join(pkg_path, "finanzas_repartidor.db")
    elif os.path.exists(pkg_path_alt):
        db_path = os.path.join(pkg_path_alt, "finanzas_repartidor.db")
    else:
        home_dir = os.path.expanduser("~")
        db_path = os.path.join(home_dir, "finanzas_repartidor.db")
    
    def init_db():
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Tabla de Movimientos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS movimientos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT,
                tipo TEXT,
                categoria TEXT,
                monto_total REAL,
                efectivo REAL,
                descuento REAL,
                gastos REAL,
                ganancia_neta REAL
            )
        """)
        
        # Tabla de Categorías
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categorias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT,
                nombre TEXT,
                porcentaje REAL DEFAULT 0.0
            )
        """)
        try:
            cursor.execute("ALTER TABLE categorias ADD COLUMN porcentaje REAL DEFAULT 0.0")
        except sqlite3.OperationalError:
            pass

        cursor.execute("SELECT COUNT(*) FROM categorias")
        if cursor.fetchone()[0] == 0:
            default_cats = [
                ("Ingreso", "Repartos App", 10.1),
                ("Ingreso", "Propinas", 0.0),
                ("Ingreso", "Saldo", 0.0),
                ("Gasto", "Gasolina", 0.0),
                ("Gasto", "Mantenimiento", 0.0),
                ("Gasto", "Comida", 0.0),
                ("Retiro", "Retiro a Efectivo", 0.0)
            ]
            cursor.executemany("INSERT INTO categorias (tipo, nombre, porcentaje) VALUES (?, ?, ?)", default_cats)
        
        # Tabla de Configuración (Para el nombre de usuario)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS config (
                clave TEXT PRIMARY KEY,
                valor TEXT
            )
        """)
        cursor.execute("SELECT COUNT(*) FROM config WHERE clave = 'nombre_usuario'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO config (clave, valor) VALUES ('nombre_usuario', 'Usuario')")

        conn.commit()
        conn.close()

    init_db()

    # --- VARIABLES GLOBALES UI ---
    txt_saludo = ft.Text("Hola, Usuario", size=20, weight=ft.FontWeight.BOLD, color=C_TEXT_MAIN)
    txt_saldo_principal = ft.Text("$0.00", size=42, weight=ft.FontWeight.BOLD, color=C_TEXT_MAIN)
    txt_ingresos_top = ft.Text("$0.00", size=18, weight=ft.FontWeight.BOLD, color=C_TEXT_MAIN)
    txt_gastos_top = ft.Text("$0.00", size=18, weight=ft.FontWeight.BOLD, color=C_TEXT_MAIN)
    
    txt_resumen_ingresos = ft.Text("$0.00", size=15, color=C_GREEN, weight=ft.FontWeight.BOLD)
    txt_resumen_gastos = ft.Text("$0.00", size=15, color=C_RED, weight=ft.FontWeight.BOLD)
    txt_resumen_impuestos = ft.Text("$0.00", size=15, color=C_ORANGE, weight=ft.FontWeight.BOLD)
    txt_resumen_digital = ft.Text("$0.00", size=15, color=C_BLUE, weight=ft.FontWeight.BOLD)
    txt_resumen_efectivo = ft.Text("$0.00", size=15, color=C_GREEN, weight=ft.FontWeight.BOLD)
    txt_resumen_neto = ft.Text("$0.00", size=22, color=C_TEXT_MAIN, weight=ft.FontWeight.BOLD)

    # Barras de las Gráficas
    barra_ingresos = ft.Container(bgcolor=C_GREEN, height=10, border_radius=5, width=10)
    barra_gastos = ft.Container(bgcolor=C_RED, height=10, border_radius=5, width=10)
    barra_impuestos = ft.Container(bgcolor=C_ORANGE, height=10, border_radius=5, width=10)
    barra_digital = ft.Container(bgcolor=C_BLUE, height=10, border_radius=5, width=10)
    barra_efectivo = ft.Container(bgcolor=C_GREEN, height=10, border_radius=5, width=10)

    lista_historial = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
    lista_categorias = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO)
    input_nombre_usuario = ft.TextField(label="Tu Nombre", expand=True, bgcolor=C_CARD, border_color="transparent", border_radius=12)

    def mostrar_notificacion(mensaje, color):
        page.snack_bar = ft.SnackBar(ft.Text(mensaje, color="#FFFFFF"), bgcolor=color, duration=2000)
        page.snack_bar.open = True
        page.update()

    def actualizar_perfil():
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT valor FROM config WHERE clave = 'nombre_usuario'")
        row = cursor.fetchone()
        conn.close()
        nombre = row[0] if row else "Usuario"
        
        txt_saludo.value = f"Hola, {nombre}"
        input_nombre_usuario.value = nombre
        page.update()

    def guardar_nombre_usuario(e):
        nuevo_nombre = input_nombre_usuario.value.strip()
        if not nuevo_nombre: return
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE config SET valor = ? WHERE clave = 'nombre_usuario'", (nuevo_nombre,))
        conn.commit()
        conn.close()
        
        actualizar_perfil()
        mostrar_notificacion("Nombre guardado correctamente", C_GREEN)

    def obtener_categorias_con_porcentaje(tipo_cat):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT nombre, porcentaje FROM categorias WHERE tipo = ?", (tipo_cat,))
        res = cursor.fetchall()
        conn.close()
        return res

    def actualizar_dashboard():
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT SUM(monto_total) FROM movimientos WHERE tipo='Ingreso'")
            t_ing_bruto = cursor.fetchone()[0] or 0.0
            
            cursor.execute("SELECT SUM(ganancia_neta) FROM movimientos WHERE tipo='Ingreso'")
            t_ing_neto = cursor.fetchone()[0] or 0.0

            cursor.execute("SELECT SUM(descuento) FROM movimientos WHERE tipo='Ingreso'")
            t_impuestos = cursor.fetchone()[0] or 0.0

            cursor.execute("SELECT SUM(gastos) FROM movimientos WHERE tipo='Gasto'")
            t_gas = cursor.fetchone()[0] or 0.0

            cursor.execute("SELECT SUM(monto_total) FROM movimientos WHERE tipo='Retiro'")
            t_ret = cursor.fetchone()[0] or 0.0

            cursor.execute("SELECT SUM(efectivo) FROM movimientos WHERE tipo='Ingreso'")
            efectivo_ing = cursor.fetchone()[0] or 0.0

            cursor.execute("SELECT SUM(efectivo) FROM movimientos WHERE tipo='Gasto'")
            efectivo_gas = cursor.fetchone()[0] or 0.0

            conn.close()

            t_net_global = t_ing_neto - t_gas

            efectivo_total = efectivo_ing + t_ret - efectivo_gas
            digital_total = (t_ing_neto - efectivo_ing) - t_ret - (t_gas - efectivo_gas)
            
            if digital_total < 0: digital_total = 0.0
            if efectivo_total < 0: efectivo_total = 0.0

            txt_ingresos_top.value = f"${t_ing_bruto:,.2f}"
            txt_gastos_top.value = f"${t_gas:,.2f}"
            txt_saldo_principal.value = f"${t_net_global:,.2f}"

            txt_resumen_ingresos.value = f"${t_ing_bruto:,.2f}"
            txt_resumen_gastos.value = f"${t_gas:,.2f}"
            txt_resumen_impuestos.value = f"${t_impuestos:,.2f}"
            
            txt_resumen_digital.value = f"${digital_total:,.2f}"
            txt_resumen_efectivo.value = f"${efectivo_total:,.2f}"
            txt_resumen_neto.value = f"${t_net_global:,.2f}"

            max_v1 = max(t_ing_bruto, t_gas, t_impuestos, 1.0)
            barra_ingresos.width = min(max((t_ing_bruto / max_v1) * 250, 10), 250)
            barra_gastos.width = min(max((t_gas / max_v1) * 250, 10), 250)
            barra_impuestos.width = min(max((t_impuestos / max_v1) * 250, 10), 250)

            max_v2 = max(digital_total, efectivo_total, 1.0)
            barra_digital.width = min(max((digital_total / max_v2) * 250, 10), 250)
            barra_efectivo.width = min(max((efectivo_total / max_v2) * 250, 10), 250)

            page.update()
        except Exception:
            pass

    # --- DIÁLOGO DE EDICIÓN COMPLETA ---
    edit_tipo_dropdown = ft.Dropdown(
        label="Tipo de Movimiento",
        options=[ft.dropdown.Option("Ingreso"), ft.dropdown.Option("Gasto"), ft.dropdown.Option("Retiro")],
        bgcolor=C_CARD, border_color="transparent", border_radius=12
    )
    edit_cat_dropdown = ft.Dropdown(label="Categoría", bgcolor=C_CARD, border_color="transparent", border_radius=12)
    edit_input_monto = ft.TextField(label="Monto Bruto ($)", prefix_text="$ ", keyboard_type=ft.KeyboardType.NUMBER, bgcolor=C_CARD, border_color="transparent", border_radius=12)
    edit_input_efectivo = ft.TextField(label="Efectivo ($)", prefix_text="$ ", keyboard_type=ft.KeyboardType.NUMBER, bgcolor=C_CARD, border_color="transparent", border_radius=12)

    def actualizar_form_edicion(e=None):
        tipo_sel = edit_tipo_dropdown.value
        cats = obtener_categorias_con_porcentaje(tipo_sel)
        edit_cat_dropdown.options = [ft.dropdown.Option(nombre) for nombre, _ in cats]
        
        if tipo_sel == "Ingreso":
            edit_input_efectivo.visible = True
        elif tipo_sel == "Gasto":
            edit_input_efectivo.visible = True
        else:
            edit_input_efectivo.visible = False
            edit_input_efectivo.value = "0"
            
        if edit_cat_dropdown.options:
            edit_cat_dropdown.value = edit_cat_dropdown.options[0].key
        page.update()

    edit_tipo_dropdown.on_change = actualizar_form_edicion

    def abrir_editar_movimiento(mov_id):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT tipo, categoria, monto_total, efectivo, gastos FROM movimientos WHERE id = ?", (mov_id,))
        row = cursor.fetchone()
        conn.close()

        if not row: return
        t_mov, cat_mov, m_tot, ef_mov, gas_mov = row

        edit_tipo_dropdown.value = t_mov
        cats = obtener_categorias_con_porcentaje(t_mov)
        edit_cat_dropdown.options = [ft.dropdown.Option(nombre) for nombre, _ in cats]
        edit_cat_dropdown.value = cat_mov if cat_mov in [o.key for o in edit_cat_dropdown.options] else (edit_cat_dropdown.options[0].key if edit_cat_dropdown.options else "")
        
        if t_mov == "Gasto":
            edit_input_monto.value = str(gas_mov if gas_mov > 0 else m_tot)
        else:
            edit_input_monto.value = str(m_tot)
            
        edit_input_efectivo.value = str(ef_mov or 0)
        page.update()

        def guardar_cambio(e):
            try:
                mt = float(edit_input_monto.value or 0)
                ef = float(edit_input_efectivo.value or 0)
            except ValueError:
                mostrar_notificacion("Ingresa números válidos", C_RED)
                return

            nuevo_tipo = edit_tipo_dropdown.value
            nueva_cat = edit_cat_dropdown.value

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            if nuevo_tipo == "Ingreso":
                if mt == 0 and ef > 0: mt = ef
                cursor.execute("SELECT porcentaje FROM categorias WHERE nombre = ? AND tipo = 'Ingreso'", (nueva_cat,))
                row_pct = cursor.fetchone()
                pct = row_pct[0] if (row_pct and row_pct[0] is not None) else 0.0
                
                descuento = mt * (pct / 100.0)
                neta = mt - descuento
                gastos_val = 0
            elif nuevo_tipo == "Gasto":
                if mt == 0 and ef > 0: mt = ef
                descuento = 0
                neta = -mt 
                gastos_val = mt
                mt = 0
            else: # Retiro
                descuento = 0
                neta = 0
                gastos_val = 0
                ef = 0

            cursor.execute("""
