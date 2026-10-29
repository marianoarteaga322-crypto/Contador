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
    C_TEXT_MAIN = "#F8FAFC"
    C_TEXT_SEC = "#64748B"

    # --- RUTA DE BASE DE DATOS ANDROID ---
    android_path = "/data/user/0/com.mariano.control/files"
    android_path_alt = "/data/data/com.mariano.control/files"
    
    if os.path.exists(android_path):
        db_path = os.path.join(android_path, "finanzas_repartidor.db")
    elif os.path.exists(android_path_alt):
        db_path = os.path.join(android_path_alt, "finanzas_repartidor.db")
    else:
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "finanzas_repartidor.db")
    
    def init_db():
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
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
        conn.commit()
        conn.close()

    init_db()

    # --- VARIABLES GLOBALES UI ---
    txt_saldo_principal = ft.Text("$0.00", size=42, weight=ft.FontWeight.BOLD, color=C_TEXT_MAIN)
    txt_ingresos_top = ft.Text("$0.00", size=18, weight=ft.FontWeight.BOLD, color=C_TEXT_MAIN)
    txt_gastos_top = ft.Text("$0.00", size=18, weight=ft.FontWeight.BOLD, color=C_TEXT_MAIN)
    
    txt_resumen_ingresos = ft.Text("$0.00", size=16, color=C_GREEN, weight=ft.FontWeight.BOLD)
    txt_resumen_gastos = ft.Text("$0.00", size=16, color=C_RED, weight=ft.FontWeight.BOLD)
    txt_resumen_retiros = ft.Text("$0.00", size=16, color=C_BLUE, weight=ft.FontWeight.BOLD)
    txt_resumen_neto = ft.Text("$0.00", size=22, color=C_TEXT_MAIN, weight=ft.FontWeight.BOLD)

    # Barras de la gráfica
    barra_ingresos = ft.Container(bgcolor=C_GREEN, height=10, border_radius=5, width=10)
    barra_gastos = ft.Container(bgcolor=C_RED, height=10, border_radius=5, width=10)
    barra_retiros = ft.Container(bgcolor=C_BLUE, height=10, border_radius=5, width=10)

    lista_historial = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
    lista_categorias = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO)

    def mostrar_notificacion(mensaje, color):
        page.snack_bar = ft.SnackBar(ft.Text(mensaje, color="#FFFFFF"), bgcolor=color, duration=2000)
        page.snack_bar.open = True
        page.update()

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
            t_ing = cursor.fetchone()[0] or 0.0
            
            cursor.execute("SELECT SUM(gastos) FROM movimientos WHERE tipo='Gasto'")
            t_gas = cursor.fetchone()[0] or 0.0

            cursor.execute("SELECT SUM(monto_total) FROM movimientos WHERE tipo='Retiro'")
            t_ret = cursor.fetchone()[0] or 0.0
            
            conn.close()

            # Saldo Neto Disponible real = Ingresos Brutos Totales - Gastos Totales - Retiros
            t_net = t_ing - t_gas - t_ret
            
            txt_ingresos_top.value = f"${t_ing:,.2f}"
            txt_gastos_top.value = f"${t_gas:,.2f}"
            txt_saldo_principal.value = f"${t_net:,.2f}"

            txt_resumen_ingresos.value = f"${t_ing:,.2f}"
            txt_resumen_gastos.value = f"${t_gas:,.2f}"
            txt_resumen_retiros.value = f"${t_ret:,.2f}"
            txt_resumen_neto.value = f"${t_net:,.2f}"

            # Actualizar proporciones de la gráfica
            max_v = max(t_ing, t_gas, t_ret, 1.0)
            barra_ingresos.width = min(max((t_ing / max_v) * 250, 10), 250)
            barra_gastos.width = min(max((t_gas / max_v) * 250, 10), 250)
            barra_retiros.width = min(max((t_ret / max_v) * 250, 10), 250)

            page.update()
        except Exception:
            pass

    # --- DIÁLOGO DE EDICIÓN DE MOVIMIENTO ---
    input_edit_monto = ft.TextField(label="Nuevo Monto ($)", prefix_text="$ ", keyboard_type=ft.KeyboardType.NUMBER, bgcolor=C_CARD, border_color="transparent", border_radius=12)

    def abrir_editar_movimiento(mov_id, monto_actual):
        input_edit_monto.value = str(monto_actual)

        def guardar_cambio(e):
            try:
                nuevo_monto = float(input_edit_monto.value or 0)
            except ValueError:
                mostrar_notificacion("Ingresa un número válido", C_RED)
                return

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT tipo FROM movimientos WHERE id = ?", (mov_id,))
            row = cursor.fetchone()
            if row:
                tipo_mov = row[0]
                if tipo_mov == "Gasto":
                    cursor.execute("UPDATE movimientos SET monto_total = 0, gastos = ?, ganancia_neta = ? WHERE id = ?", (nuevo_monto, -nuevo_monto, mov_id))
                elif tipo_mov == "Retiro":
                    cursor.execute("UPDATE movimientos SET monto_total = ? WHERE id = ?", (nuevo_monto, mov_id))
                else: # Ingreso
                    cursor.execute("UPDATE movimientos SET monto_total = ?, ganancia_neta = ? WHERE id = ?", (nuevo_monto, nuevo_monto, mov_id))
            conn.commit()
            conn.close()

            page.dialog.open = False
            page.update()
            actualizar_dashboard()
            cargar_historial()
            mostrar_notificacion("¡Movimiento actualizado!", C_GREEN)

        page.dialog = ft.AlertDialog(
            bgcolor=C_CARD,
            title=ft.Text("Editar Movimiento", color=C_TEXT_MAIN, weight=ft.FontWeight.BOLD),
            content=ft.Column([input_edit_monto], tight=True),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: cerrar_dialogo()),
                ft.ElevatedButton("Guardar", bgcolor=C_BLUE, color="#FFFFFF", on_click=guardar_cambio)
            ]
        )
        page.dialog.open = True
        page.update()

    # --- DIÁLOGOS DE DESGLOSE ---
    def mostrar_desglose_ingresos(e):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT SUM(monto_total), SUM(efectivo) FROM movimientos WHERE tipo = 'Ingreso'")
            res = cursor.fetchone()
            
            cursor.execute("SELECT SUM(monto_total) FROM movimientos WHERE tipo = 'Retiro'")
            t_ret = cursor.fetchone()[0] or 0.0
            conn.close()
            
            t_total = res[0] or 0.0
            t_efectivo_ingreso = res[1] or 0.0
            t_efectivo_total = t_efectivo_ingreso + t_ret
            
            t_digital = t_total - t_efectivo_ingreso
            if t_digital < 0: t_digital = 0.0

            page.dialog = ft.AlertDialog(
                bgcolor=C_CARD,
                title=ft.Text("Desglose de Ingresos y Efectivo", color=C_TEXT_MAIN, weight=ft.FontWeight.BOLD),
                content=ft.Column([
                    ft.ListTile(leading=ft.Icon(ft.icons.PHONE_ANDROID, color=C_BLUE), title=ft.Text("Apps (Digital)", color=C_TEXT_SEC, size=13), subtitle=ft.Text(f"${t_digital:,.2f}", color=C_TEXT_MAIN, size=18, weight=ft.FontWeight.BOLD)),
                    ft.ListTile(leading=ft.Icon(ft.icons.ATTACH_MONEY, color=C_GREEN), title=ft.Text("Efectivo Total (Incluye Retiros)", color=C_TEXT_SEC, size=13), subtitle=ft.Text(f"${t_efectivo_total:,.2f}", color=C_TEXT_MAIN, size=18, weight=ft.FontWeight.BOLD)),
                    ft.Divider(color="#334155"),
                    ft.Row([ft.Text("Total Ingresos Brutos:", color=C_TEXT_MAIN, weight=ft.FontWeight.BOLD), ft.Text(f"${t_total:,.2f}", color=C_GREEN, weight=ft.FontWeight.BOLD, size=16)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                ], tight=True),
                actions=[ft.TextButton("Cerrar", on_click=lambda e: cerrar_dialogo())]
            )
            page.dialog.open = True
            page.update()
        except Exception:
            pass

    def mostrar_desglose_gastos(e):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT SUM(gastos), SUM(efectivo) FROM movimientos WHERE tipo = 'Gasto'")
            res = cursor.fetchone()
            conn.close()
            
            t_total = res[0] or 0.0
            t_efectivo = res[1] or 0.0
            t_tarjeta = t_total - t_efectivo
            if t_tarjeta < 0: t_tarjeta = 0.0

            page.dialog = ft.AlertDialog(
                bgcolor=C_CARD,
                title=ft.Text("Desglose de Gastos", color=C_TEXT_MAIN, weight=ft.FontWeight.BOLD),
                content=ft.Column([
                    ft.ListTile(leading=ft.Icon(ft.icons.CREDIT_CARD, color=C_BLUE), title=ft.Text("Pagado con Tarjeta", color=C_TEXT_SEC, size=13), subtitle=ft.Text(f"${t_tarjeta:,.2f}", color=C_TEXT_MAIN, size=18, weight=ft.FontWeight.BOLD)),
                    ft.ListTile(leading=ft.Icon(ft.icons.ATTACH_MONEY, color=C_RED), title=ft.Text("Pagado en Efectivo", color=C_TEXT_SEC, size=13), subtitle=ft.Text(f"${t_efectivo:,.2f}", color=C_TEXT_MAIN, size=18, weight=ft.FontWeight.BOLD)),
                    ft.Divider(color="#334155"),
                    ft.Row([ft.Text("Total Gastos:", color=C_TEXT_MAIN, weight=ft.FontWeight.BOLD), ft.Text(f"${t_total:,.2f}", color=C_RED, weight=ft.FontWeight.BOLD, size=16)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                ], tight=True),
                actions=[ft.TextButton("Cerrar", on_click=lambda e: cerrar_dialogo())]
            )
            page.dialog.open = True
            page.update()
        except Exception:
            pass

    def cerrar_dialogo():
        page.dialog.open = False
        page.update()

    def borrar_movimiento(mov_id):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM movimientos WHERE id = ?", (mov_id,))
        conn.commit()
        conn.close()
        actualizar_dashboard()
        cargar_historial()
        mostrar_notificacion("Registro eliminado", C_RED)

    def cargar_historial():
        try:
            lista_historial.controls.clear()
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id, fecha, categoria, ganancia_neta, tipo, monto_total, gastos FROM movimientos ORDER BY id DESC LIMIT 30")
            rows = cursor.fetchall()
            conn.close()

            if not rows:
                lista_historial.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.icons.INSERT_CHART_OUTLINED, size=80, color="#1E293B"),
                            ft.Text("Sin movimientos registrados", color=C_TEXT_SEC, size=14)
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=40, alignment=ft.alignment.center
                    )
                )
            else:
                for row in rows:
                    mov_id = row[0]
                    fecha = row[1] or ""
                    categoria = row[2] or "General"
                    neta = row[3] if row[3] is not None else 0.0
                    tipo = row[4] or "Ingreso"
                    monto_t = row[5] if row[5] is not None else 0.0
                    gasto_t = row[6] if row[6] is not None else 0.0

                    es_ingreso = (tipo == "Ingreso")
                    es_retiro = (tipo == "Retiro")
                    
                    color_monto = C_GREEN if es_ingreso else (C_BLUE if es_retiro else C_RED)
                    icono_mov = ft.icons.SWAP_HORIZ if es_retiro else (ft.icons.CHECK_CIRCLE if es_ingreso else ft.icons.REMOVE_CIRCLE)
                    bg_icono = "#1E3A8A" if es_retiro else ("#064E3B" if es_ingreso else "#450A0A")

                    if es_retiro:
                        texto_monto = f"⇄ ${monto_t:,.2f}"
                        val_para_editar = monto_t
                    elif es_ingreso:
                        texto_monto = f"+ ${monto_t if monto_t > 0 else neta:,.2f}"
                        val_para_editar = monto_t if monto_t > 0 else neta
                    else:
                        texto_monto = f"- ${abs(gasto_t if gasto_t > 0 else neta):,.2f}"
                        val_para_editar = abs(gasto_t if gasto_t > 0 else neta)

                    lista_historial.controls.append(
                        ft.Container(
                            content=ft.Row([
                                ft.Row([
                                    ft.Container(
                                        content=ft.Icon(icono_mov, color=color_monto, size=20), 
                                        bgcolor=bg_icono, padding=10, border_radius=12
                                    ),
                                    ft.Column([
                                        ft.Text(categoria, color=C_TEXT_MAIN, weight=ft.FontWeight.BOLD, size=15),
                                        ft.Text(f"{fecha}", color=C_TEXT_SEC, size=11)
                                    ], spacing=2, alignment=ft.MainAxisAlignment.CENTER)
                                ], spacing=12),
                                ft.Row([
                                    ft.Text(texto_monto, color=color_monto, weight=ft.FontWeight.BOLD, size=13),
                                    ft.IconButton(icon=ft.icons.EDIT_OUTLINED, icon_color=C_BLUE, icon_size=16, tooltip="Editar", on_click=lambda e, m=mov_id, val=val_para_editar: abrir_editar_movimiento(m, val)),
                                    ft.IconButton(icon=ft.icons.DELETE_OUTLINE, icon_color=C_RED, icon_size=16, tooltip="Eliminar", on_click=lambda e, m=mov_id: borrar_movimiento(m))
                                ], spacing=2)
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            bgcolor=C_CARD, padding=12, border_radius=15
                        )
                    )
            page.update()
        except Exception as ex:
            print("Error cargando historial:", ex)

    # --- PANEL DE NOTIFICACIONES ---
    def abrir_notificaciones(e):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT SUM(descuento) FROM movimientos")
            res = cursor.fetchone()
            conn.close()
            total_descuentos = res[0] or 0.0

            page.bottom_sheet = ft.BottomSheet(
                ft.Container(
                    bgcolor=C_CARD, padding=25, border_radius=ft.border_radius.vertical(top=20),
                    content=ft.Column([
                        ft.Row([
                            ft.Text("Resumen y Alertas", size=20, weight=ft.FontWeight.BOLD, color=C_TEXT_MAIN),
                            ft.IconButton(ft.icons.CLOSE, icon_color=C_TEXT_SEC, on_click=lambda e: cerrar_sheet())
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Divider(color="#334155"),
                        ft.ListTile(leading=ft.Icon(ft.icons.LIGHTBULB_OUTLINE, color="#FBBF24"), title=ft.Text("Consejo Financiero", color=C_TEXT_MAIN, weight=ft.FontWeight.BOLD), subtitle=ft.Text("Recuerda separar tus retenciones e impuestos de tus ganancias.", color=C_TEXT_SEC)),
                        ft.ListTile(leading=ft.Icon(ft.icons.RECEIPT_LONG, color=C_BLUE), title=ft.Text(f"Descuentos Acumulados: ${total_descuentos:,.2f}", color=C_TEXT_MAIN, weight=ft.FontWeight.BOLD), subtitle=ft.Text("Total retenido de tus categorías configuradas.", color=C_TEXT_SEC)),
                        ft.Container(height=10)
                    ], tight=True)
                )
            )
            page.bottom_sheet.open = True
            page.update()
        except Exception:
            pass

    def cerrar_sheet():
        page.bottom_sheet.open = False
        page.update()

    # --- 1. BIENVENIDA ---
    vista_bienvenida = ft.Container(
        expand=True,
        gradient=ft.LinearGradient(begin=ft.alignment.top_left, end=ft.alignment.bottom_right, colors=[C_PURPLE, C_BG, C_BG]),
        content=ft.Column([
            ft.Container(height=100),
            ft.Icon(ft.icons.MULTILINE_CHART, size=100, color=C_BLUE),
            ft.Text("ConFin", size=40, weight=ft.FontWeight.BOLD, color=C_TEXT_MAIN, text_align=ft.TextAlign.CENTER),
            ft.Text("Gestiona tus finanzas de forma inteligente.", size=16, color=C_TEXT_SEC, text_align=ft.TextAlign.CENTER),
            ft.Container(expand=True),
            ft.ElevatedButton("Comenzar", bgcolor=C_BLUE, color="#FFFFFF", width=300, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=15)), on_click=lambda e: page.go("/dashboard")),
            ft.Container(height=40)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    )

    # --- 2. DASHBOARD (INICIO) ---
    card_ingresos = ft.Container(
        expand=True,
        content=ft.GestureDetector(
            on_tap=mostrar_desglose_ingresos,
            content=ft.Container(
                content=ft.Row([
                    ft.Container(content=ft.Icon(ft.icons.ARROW_UPWARD, color=C_GREEN, size=16), bgcolor="#064E3B", padding=8, border_radius=10),
                    ft.Column([ft.Text("Ingresos", size=12, color=C_TEXT_SEC), txt_ingresos_top], spacing=0)
                ]),
                bgcolor=C_CARD, padding=15, border_radius=15
            )
        )
    )

    card_gastos = ft.Container(
        expand=True,
        content=ft.GestureDetector(
            on_tap=mostrar_desglose_gastos,
            content=ft.Container(
                content=ft.Row([
                    ft.Container(content=ft.Icon(ft.icons.ARROW_DOWNWARD, color=C_RED, size=16), bgcolor="#450A0A", padding=8, border_radius=10),
                    ft.Column([ft.Text("Gastos", size=12, color=C_TEXT_SEC), txt_gastos_top], spacing=0)
                ]),
                bgcolor=C_CARD, padding=15, border_radius=15
            )
        )
    )

    vista_dashboard = ft.Container(
        expand=True,
        gradient=ft.LinearGradient(begin=ft.alignment.top_center, end=ft.alignment.center, colors=["#1E1B4B", C_BG]),
        padding=20,
        content=ft.Column([
            ft.Row([
                ft.Text("Hola, Mariano", size=20, weight=ft.FontWeight.BOLD, color=C_TEXT_MAIN),
                ft.IconButton(ft.icons.NOTIFICATIONS_OUTLINED, icon_color=C_TEXT_MAIN, on_click=abrir_notificaciones)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(height=10),
            ft.Text("Saldo Neto Disponible", size=14, color=C_TEXT_SEC, text_align=ft.TextAlign.CENTER),
            ft.Container(content=txt_saldo_principal, alignment=ft.alignment.center),
            ft.Container(height=20),
            ft.Row([card_ingresos, card_gastos], alignment=ft.MainAxisAlignment.CENTER, spacing=15),
            ft.Container(height=20),
            ft.Text("Últimos Registros", size=16, weight=ft.FontWeight.BOLD, color=C_TEXT_MAIN),
            ft.Container(content=lista_historial, expand=True)
        ])
    )

    # --- 3. VISTA DE RESUMEN CON GRÁFICA VISUAL ---
    vista_resumen = ft.Container(
        expand=True,
        gradient=ft.LinearGradient(begin=ft.alignment.top_center, end=ft.alignment.center, colors=["#1E1B4B", C_BG]),
        padding=20,
        content=ft.Column([
            ft.Container(height=30),
            ft.Text("Resumen Financiero", size=26, weight=ft.FontWeight.BOLD, color=C_TEXT_MAIN),
            ft.Text("Gráfica y balance general", color=C_TEXT_SEC, size=14),
            ft.Container(height=15),
            
            # Tarjeta de Gráfica Proporcional
            ft.Card(
                color=C_CARD,
                content=ft.Container(
                    padding=20,
                    content=ft.Column([
                        ft.Text("Gráfica de Movimientos", size=14, weight=ft.FontWeight.BOLD, color=C_TEXT_MAIN),
                        ft.Container(height=10),
                        ft.Row([ft.Text("Ingresos", size=12, color=C_GREEN), txt_resumen_ingresos], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        barra_ingresos,
                        ft.Container(height=8),
                        ft.Row([ft.Text("Gastos", size=12, color=C_RED), txt_resumen_gastos], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        barra_gastos,
                        ft.Container(height=8),
                        ft.Row([ft.Text("Retiros", size=12, color=C_BLUE), txt_resumen_retiros], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        barra_retiros,
                    ])
                )
            ),
            ft.Container(height=10),
            
            # Tarjeta de Estadísticas Generales
            ft.Card(
                color=C_CARD,
                content=ft.Container(
                    padding=20,
                    content=ft.Column([
                        ft.Text("ESTADÍSTICAS GENERALES", size=12, color=C_PURPLE, weight=ft.FontWeight.BOLD),
                        ft.Divider(color="#334155"),
                        ft.Row([ft.Text("Balance Neto Global:", color=C_TEXT_MAIN, weight=ft.FontWeight.BOLD), txt_resumen_neto], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ], spacing=10)
                )
            ),
        ], scroll=ft.ScrollMode.AUTO)
    )

    # --- 4. REGISTRO ---
    tipo_registro = ft.Dropdown(
        label="Tipo de Movimiento",
        options=[ft.dropdown.Option("Ingreso"), ft.dropdown.Option("Gasto"), ft.dropdown.Option("Retiro")],
        value="Ingreso", bgcolor=C_CARD, border_color="transparent", border_radius=12
    )
    input_monto = ft.TextField(label="Monto Bruto ($) (Total)", prefix_text="$ ", keyboard_type=ft.KeyboardType.NUMBER, bgcolor=C_CARD, border_color="transparent", border_radius=12)
    input_efectivo = ft.TextField(label="¿Cuánto de eso fue en efectivo? ($)", prefix_text="$ ", keyboard_type=ft.KeyboardType.NUMBER, bgcolor=C_CARD, border_color="transparent", border_radius=12)
    cat_dropdown = ft.Dropdown(label="Categoría", bgcolor=C_CARD, border_color="transparent", border_radius=12)
    
    _cat_porcentajes = {}

    def actualizar_form_registro(e=None):
        nonlocal _cat_porcentajes
        _cat_porcentajes = {}
        
        if tipo_registro.value == "Ingreso":
            input_efectivo.visible = True
            input_efectivo.label = "¿Cuánto de eso fue en efectivo? ($)"
            input_monto.label = "Monto Bruto ($) (Total)"
            cats = obtener_categorias_con_porcentaje("Ingreso")
            cat_dropdown.options = [ft.dropdown.Option(nombre) for nombre, _ in cats]
            for nombre, pct in cats:
                _cat_porcentajes[nombre] = pct
        elif tipo_registro.value == "Gasto":
            input_efectivo.visible = True
            input_efectivo.label = "¿Cuánto de eso fue en efectivo? ($)"
            input_monto.label = "Monto Total del Gasto ($)"
            cats = obtener_categorias_con_porcentaje("Gasto")
            cat_dropdown.options = [ft.dropdown.Option(nombre) for nombre, _ in cats]
        else: # Retiro
            input_efectivo.visible = False
            input_efectivo.value = "0"
            input_monto.label = "Monto del Retiro ($)"
            cats = obtener_categorias_con_porcentaje("Retiro")
            cat_dropdown.options = [ft.dropdown.Option(nombre) for nombre, _ in cats]
        
        if cat_dropdown.options:
            cat_dropdown.value = cat_dropdown.options[0].key
        page.update()

    tipo_registro.on_change = actualizar_form_registro

    def guardar_cierre(e):
        try:
            mt = float(input_monto.value or 0)
            ef = float(input_efectivo.value or 0)
        except ValueError:
            mostrar_notificacion("Ingresa números válidos", C_RED)
            return

        fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        tipo = tipo_registro.value
        categoria_seleccionada = cat_dropdown.value

        if tipo == "Ingreso":
            if mt == 0 and ef > 0: mt = ef
            pct = _cat_porcentajes.get(categoria_seleccionada, 0.0)
            descuento = mt * (pct / 100.0)
            neta = mt - descuento
            gastos_val = 0
        elif tipo == "Gasto":
            if mt == 0 and ef > 0: mt = ef
            descuento = 0
            neta = -mt 
            gastos_val = mt
            mt = 0
        else: # Retiro
            descuento = 0
            neta = 0
            gastos_val = 0

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO movimientos (fecha, tipo, categoria, monto_total, efectivo, descuento, gastos, ganancia_neta) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       (fecha, tipo, categoria_seleccionada, mt, ef, descuento, gastos_val, neta))
        conn.commit()
        conn.close()

        input_monto.value, input_efectivo.value = "", ""
        actualizar_dashboard()
        cargar_historial()
        mostrar_notificacion("¡Registro guardado con éxito!", C_GREEN)
        page.go("/dashboard")

    vista_registro = ft.Container(
        expand=True, bgcolor=C_BG, padding=20,
        content=ft.Column([
            ft.Row([
                ft.IconButton(ft.icons.ARROW_BACK_IOS, icon_color=C_TEXT_MAIN, on_click=lambda e: page.go("/dashboard")),
                ft.Text("Nuevo Registro", size=24, weight=ft.FontWeight.BOLD, color=C_TEXT_MAIN)
            ]),
            ft.Text("Selecciona el tipo de movimiento y categoría.", color=C_TEXT_SEC),
            ft.Container(height=15),
            tipo_registro, input_monto, input_efectivo, cat_dropdown,
            ft.Container(height=20),
            ft.ElevatedButton("Guardar Registro", bgcolor=C_BLUE, color="#FFFFFF", width=float('inf'), height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=15)), on_click=guardar_cierre)
        ], scroll=ft.ScrollMode.AUTO)
    )

    # --- 5. AJUSTES ---
    input_n_cat = ft.TextField(label="Nombre de categoría", expand=True, bgcolor=C_CARD, border_color="transparent", border_radius=12)
    tipo_n_cat = ft.Dropdown(
        options=[ft.dropdown.Option("Ingreso"), ft.dropdown.Option("Gasto"), ft.dropdown.Option("Retiro")], 
        value="Ingreso", width=120, bgcolor=C_CARD, border_color="transparent", border_radius=12
    )
    input_pct_cat = ft.TextField(label="% Descuento fijo", value="0.0", width=120, keyboard_type=ft.KeyboardType.NUMBER, bgcolor=C_CARD, border_color="transparent", border_radius=12)

    def actualizar_form_ajustes(e=None):
        if tipo_n_cat.value == "Ingreso":
            input_pct_cat.visible = True
        else:
            input_pct_cat.visible = False
            input_pct_cat.value = "0.0"
        page.update()

    tipo_n_cat.on_change = actualizar_form_ajustes

    def refrescar_cats():
        lista_categorias.controls.clear()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, tipo, nombre, porcentaje FROM categorias")
        for r in cursor.fetchall():
            sub_text = f"{r[1]} • Descuento: {r[3]}%" if r[1] == "Ingreso" else r[1]
            lista_categorias.controls.append(
                ft.ListTile(
                    title=ft.Text(r[2], color=C_TEXT_MAIN), 
                    subtitle=ft.Text(sub_text, color=C_TEXT_SEC),
                    trailing=ft.IconButton(ft.icons.DELETE, icon_color=C_RED, on_click=lambda e, cid=r[0]: borrar_cat(cid))
                )
            )
        conn.close()
        actualizar_form_registro()

    def borrar_cat(cid):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM categorias WHERE id = ?", (cid,))
        conn.commit()
        conn.close()
        refrescar_cats()

    def agregar_cat(e):
        if not input_n_cat.value: return
        try:
            pct_val = float(input_pct_cat.value) if tipo_n_cat.value == "Ingreso" else 0.0
        except ValueError:
            pct_val = 0.0

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO categorias (tipo, nombre, porcentaje) VALUES (?, ?, ?)", (tipo_n_cat.value, input_n_cat.value, pct_val))
        conn.commit()
        conn.close()
        
        input_n_cat.value = ""
        input_pct_cat.value = "0.0"
        refrescar_cats()
        mostrar_notificacion("Categoría agregada con éxito", C_GREEN)

    vista_ajustes = ft.Container(
        expand=True, bgcolor=C_BG, padding=20,
        content=ft.Column([
            ft.Container(height=30),
            ft.Text("Ajustes", size=28, weight=ft.FontWeight.BOLD, color=C_TEXT_MAIN),
            ft.Text("Administra tus categorías y porcentajes", color=C_TEXT_SEC),
            ft.Container(height=20),
            ft.Row([tipo_n_cat, input_n_cat]),
            input_pct_cat,
            ft.Container(height=5),
            ft.ElevatedButton("Agregar Categoría", bgcolor=C_PURPLE, color="#FFFFFF", width=float('inf'), height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)), on_click=agregar_cat),
            ft.Container(height=20),
            ft.Text("Categorías Actuales", weight=ft.FontWeight.BOLD, color=C_TEXT_MAIN),
            ft.Container(content=lista_categorias, expand=True)
        ])
    )

    # --- NAVEGACIÓN Y ENRUTAMIENTO CON 3 PESTAÑAS ---
    nav_bar = ft.NavigationBar(
        bgcolor=C_BG, selected_index=0,
        destinations=[
            ft.NavigationBarDestination(icon=ft.icons.HOME_OUTLINED, selected_icon=ft.icons.HOME, label="Inicio"),
            ft.NavigationBarDestination(icon=ft.icons.BAR_CHART_OUTLINED, selected_icon=ft.icons.BAR_CHART, label="Resumen"),
            ft.NavigationBarDestination(icon=ft.icons.SETTINGS_OUTLINED, selected_icon=ft.icons.SETTINGS, label="Ajustes"),
        ],
        on_change=lambda e: cambiar_tab(e.control.selected_index)
    )

    fab = ft.FloatingActionButton(icon=ft.icons.ADD, bgcolor=C_BLUE, shape=ft.RoundedRectangleBorder(radius=15), on_click=lambda e: page.go("/registro"))
    contenedor_base = ft.Stack([vista_dashboard, vista_resumen, vista_ajustes], expand=True)
    
    def cambiar_tab(index):
        vista_dashboard.visible = (index == 0)
        vista_resumen.visible = (index == 1)
        vista_ajustes.visible = (index == 2)
        page.update()

    def route_change(route):
        page.views.clear()
        
        if page.route == "/welcome":
            page.views.append(ft.View("/welcome", [ft.SafeArea(vista_bienvenida, expand=True)], padding=0, bgcolor=C_BG))
        elif page.route == "/registro":
            page.views.append(ft.View("/registro", [ft.SafeArea(vista_registro, expand=True)], padding=0, bgcolor=C_BG))
        else:
            page.views.append(
                ft.View(
                    "/dashboard",
                    [ft.SafeArea(contenedor_base, expand=True)],
                    navigation_bar=nav_bar,
                    floating_action_button=fab,
                    padding=0, bgcolor=C_BG
                )
            )
        page.update()

    def view_pop(view):
        page.views.pop()
        page.go(page.views[-1].route)

    page.on_route_change = route_change
    page.on_view_pop = view_pop

    # Inicialización segura
    try:
        actualizar_dashboard()
        cargar_historial()
        refrescar_cats()
        actualizar_form_ajustes()
        cambiar_tab(0)
    except Exception:
        pass
    
    page.go("/welcome")

ft.app(target=main)
