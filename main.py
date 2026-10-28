import flet as ft
import sqlite3
import datetime
import os
import time

def main(page: ft.Page):
    # --- CONFIGURACIÓN BASE MÓVIL ---
    page.title = "Control Financiero"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#0B0E17"
    # IMPORTANTE: Eliminamos window_width y window_height para forzar pantalla completa en Android

    # Paleta de colores Premium
    C_BG = "#0B0E17"
    C_CARD = "#151B2B"
    C_BLUE = "#3B82F6"
    C_PURPLE = "#8B5CF6"
    C_GREEN = "#10B981"
    C_RED = "#EF4444"
    C_TEXT_MAIN = "#F8FAFC"
    C_TEXT_SEC = "#64748B"

    # --- RUTAS DE BASE DE DATOS ANDROID ---
    android_path = "/data/user/0/com.flet.contador/files"
    android_path_alt = "/data/data/com.flet.contador/files"
    
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
                isr REAL,
                iva REAL,
                gastos REAL,
                ganancia_neta REAL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categorias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT,
                nombre TEXT
            )
        """)
        # Forzar categorías predeterminadas si está vacío
        cursor.execute("SELECT COUNT(*) FROM categorias")
        if cursor.fetchone()[0] == 0:
            default_cats = [
                ("Ingreso", "Repartos App"),
                ("Ingreso", "Propinas"),
                ("Gasto", "Gasolina"),
                ("Gasto", "Mantenimiento"),
                ("Gasto", "Comida")
            ]
            cursor.executemany("INSERT INTO categorias (tipo, nombre) VALUES (?, ?)", default_cats)
        conn.commit()
        conn.close()

    init_db()

    # --- ACTUALIZAR TIEMPO DE SESIÓN ---
    def registrar_actividad():
        page.client_storage.set("last_active", time.time())

    # --- VARIABLES GLOBALES UI ---
    txt_saldo_principal = ft.Text("$0.00", size=42, weight=ft.FontWeight.BOLD, color=C_TEXT_MAIN)
    txt_ingresos_top = ft.Text("$0.00", size=18, weight=ft.FontWeight.BOLD, color=C_TEXT_MAIN)
    txt_gastos_top = ft.Text("$0.00", size=18, weight=ft.FontWeight.BOLD, color=C_TEXT_MAIN)
    
    lista_historial = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
    lista_categorias = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO)

    def mostrar_notificacion(mensaje, color):
        page.snack_bar = ft.SnackBar(ft.Text(mensaje, color="#FFFFFF"), bgcolor=color, duration=2000)
        page.snack_bar.open = True
        page.update()

    def obtener_categorias(tipo_cat):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT nombre FROM categorias WHERE tipo = ?", (tipo_cat,))
        cats = [row[0] for row in cursor.fetchall()]
        conn.close()
        return cats

    def actualizar_dashboard():
        registrar_actividad()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(monto_total), SUM(gastos), SUM(ganancia_neta) FROM movimientos")
        res = cursor.fetchone()
        conn.close()

        t_ing = res[0] or 0.0
        t_gas = res[1] or 0.0
        t_net = res[2] or 0.0

        txt_ingresos_top.value = f"${t_ing:,.2f}"
        txt_gastos_top.value = f"${t_gas:,.2f}"
        txt_saldo_principal.value = f"${t_net:,.2f}"
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
        lista_historial.controls.clear()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, fecha, categoria, monto_total, ganancia_neta, tipo FROM movimientos ORDER BY id DESC LIMIT 30")
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
                mov_id, fecha, categoria, total, neta, tipo = row
                es_ingreso = (tipo == "Ingreso")
                lista_historial.controls.append(
                    ft.Container(
                        content=ft.ListTile(
                            leading=ft.Container(
                                content=ft.Icon(ft.icons.CHECK_CIRCLE if es_ingreso else ft.icons.REMOVE_CIRCLE, color=C_GREEN if es_ingreso else C_RED), 
                                bgcolor="#064E3B" if es_ingreso else "#450A0A", padding=10, border_radius=12
                            ),
                            title=ft.Text(categoria, color=C_TEXT_MAIN, weight=ft.FontWeight.BOLD),
                            subtitle=ft.Text(f"{fecha}", color=C_TEXT_SEC, size=12),
                            trailing=ft.Column([
                                ft.Text(f"{'+' if es_ingreso else '-'} ${abs(neta):,.2f}", color=C_GREEN if es_ingreso else C_RED, weight=ft.FontWeight.BOLD),
                                ft.IconButton(icon=ft.icons.DELETE, icon_color=C_RED, icon_size=16, on_click=lambda e, m=mov_id: borrar_movimiento(m))
                            ], alignment=ft.MainAxisAlignment.CENTER, spacing=0)
                        ),
                        bgcolor=C_CARD, border_radius=15
                    )
                )
        page.update()

    # --- COMPONENTES VISUALES ---

    # 1. BIENVENIDA
    vista_bienvenida = ft.Container(
        expand=True,
        gradient=ft.LinearGradient(begin=ft.alignment.top_left, end=ft.alignment.bottom_right, colors=[C_PURPLE, C_BG, C_BG]),
        content=ft.Column([
            ft.Container(height=100),
            ft.Icon(ft.icons.MULTILINE_CHART, size=100, color=C_BLUE),
            ft.Text("Control\nFinanciero", size=40, weight=ft.FontWeight.BOLD, color=C_TEXT_MAIN, text_align=ft.TextAlign.CENTER),
            ft.Text("Gestiona tus repartos de forma inteligente.", size=16, color=C_TEXT_SEC, text_align=ft.TextAlign.CENTER),
            ft.Container(expand=True),
            ft.ElevatedButton("Comenzar", bgcolor=C_BLUE, color="#FFFFFF", width=300, height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=15)), on_click=lambda e: page.go("/")),
            ft.Container(height=40)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    )

    # 2. DASHBOARD
    vista_dashboard = ft.Container(
        expand=True,
        gradient=ft.LinearGradient(begin=ft.alignment.top_center, end=ft.alignment.center, colors=["#1E1B4B", C_BG]),
        padding=20,
        content=ft.Column([
            ft.Row([
                ft.Row([
                    ft.CircleAvatar(content=ft.Text("M", weight=ft.FontWeight.BOLD), bgcolor=C_BLUE, color="#FFFFFF"),
                    ft.Text("Hola, Mariano", size=18, weight=ft.FontWeight.BOLD, color=C_TEXT_MAIN)
                ]),
                ft.IconButton(ft.icons.NOTIFICATIONS, icon_color=C_TEXT_SEC)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(height=20),
            ft.Text("Saldo Neto Disponible", size=14, color=C_TEXT_SEC, text_align=ft.TextAlign.CENTER),
            ft.Container(content=txt_saldo_principal, alignment=ft.alignment.center),
            ft.Container(height=20),
            ft.Row([
                ft.Container(content=ft.Row([
                    ft.Container(content=ft.Icon(ft.icons.ARROW_UPWARD, color=C_GREEN, size=16), bgcolor="#064E3B", padding=8, border_radius=10),
                    ft.Column([ft.Text("Ingresos", size=12, color=C_TEXT_SEC), txt_ingresos_top], spacing=0)
                ]), bgcolor=C_CARD, padding=15, border_radius=15, expand=True),
                ft.Container(content=ft.Row([
                    ft.Container(content=ft.Icon(ft.icons.ARROW_DOWNWARD, color=C_RED, size=16), bgcolor="#450A0A", padding=8, border_radius=10),
                    ft.Column([ft.Text("Gastos", size=12, color=C_TEXT_SEC), txt_gastos_top], spacing=0)
                ]), bgcolor=C_CARD, padding=15, border_radius=15, expand=True)
            ], spacing=15),
            ft.Container(height=20),
            ft.Text("Últimos Registros", size=16, weight=ft.FontWeight.BOLD, color=C_TEXT_MAIN),
            ft.Container(content=lista_historial, expand=True)
        ])
    )

    # 3. REGISTRO (FORMULARIO INTELIGENTE)
    tipo_registro = ft.Dropdown(
        label="Tipo de Movimiento",
        options=[ft.dropdown.Option("Ingreso"), ft.dropdown.Option("Gasto")],
        value="Ingreso", bgcolor=C_CARD, border_color="transparent", border_radius=12
    )
    input_monto = ft.TextField(label="Monto Bruto ($)", prefix_text="$ ", keyboard_type=ft.KeyboardType.NUMBER, bgcolor=C_CARD, border_color="transparent", border_radius=12)
    input_efectivo = ft.TextField(label="Efectivo Recibido ($)", prefix_text="$ ", keyboard_type=ft.KeyboardType.NUMBER, bgcolor=C_CARD, border_color="transparent", border_radius=12)
    cat_dropdown = ft.Dropdown(label="Categoría", bgcolor=C_CARD, border_color="transparent", border_radius=12)

    def actualizar_form_registro(e=None):
        if tipo_registro.value == "Ingreso":
            input_efectivo.visible = True
            input_monto.label = "Ganancia Bruta del Día ($)"
            cat_dropdown.options = [ft.dropdown.Option(c) for c in obtener_categorias("Ingreso")]
        else:
            input_efectivo.visible = False
            input_efectivo.value = "0"
            input_monto.label = "Monto del Gasto ($)"
            cat_dropdown.options = [ft.dropdown.Option(c) for c in obtener_categorias("Gasto")]
        
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

        if tipo == "Ingreso":
            isr = (mt + ef) * 0.021
            iva = (mt + ef) * 0.08
            neta = mt - (isr + iva)
            gastos_val = 0
        else:
            isr = 0
            iva = 0
            neta = -mt # Resta a la ganancia
            gastos_val = mt
            mt = 0 # No es ingreso

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO movimientos (fecha, tipo, categoria, monto_total, efectivo, isr, iva, gastos, ganancia_neta) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (fecha, tipo, cat_dropdown.value, mt, ef, isr, iva, gastos_val, neta))
        conn.commit()
        conn.close()

        input_monto.value, input_efectivo.value = "", ""
        actualizar_dashboard()
        cargar_historial()
        mostrar_notificacion("¡Registro guardado con éxito!", C_GREEN)
        page.go("/") # Vuelve al inicio

    vista_registro = ft.Container(
        expand=True, bgcolor=C_BG, padding=20,
        content=ft.Column([
            ft.Row([
                ft.IconButton(ft.icons.ARROW_BACK_IOS, icon_color=C_TEXT_MAIN, on_click=lambda e: page.go("/")),
                ft.Text("Nuevo Registro", size=24, weight=ft.FontWeight.BOLD, color=C_TEXT_MAIN)
            ]),
            ft.Text("Selecciona el tipo de movimiento a registrar.", color=C_TEXT_SEC),
            ft.Container(height=20),
            tipo_registro, input_monto, input_efectivo, cat_dropdown,
            ft.Container(height=20),
            ft.ElevatedButton("Guardar Registro", bgcolor=C_BLUE, color="#FFFFFF", width=float('inf'), height=55, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=15)), on_click=guardar_cierre)
        ])
    )

    # 4. AJUSTES
    input_n_cat = ft.TextField(label="Nombre de categoría", expand=True, bgcolor=C_CARD, border_color="transparent", border_radius=12)
    tipo_n_cat = ft.Dropdown(options=[ft.dropdown.Option("Ingreso"), ft.dropdown.Option("Gasto")], value="Ingreso", width=120, bgcolor=C_CARD, border_color="transparent", border_radius=12)

    def refrescar_cats():
        lista_categorias.controls.clear()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, tipo, nombre FROM categorias")
        for r in cursor.fetchall():
            lista_categorias.controls.append(
                ft.ListTile(
                    title=ft.Text(r[2], color=C_TEXT_MAIN), subtitle=ft.Text(r[1], color=C_TEXT_SEC),
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
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO categorias (tipo, nombre) VALUES (?, ?)", (tipo_n_cat.value, input_n_cat.value))
        conn.commit()
        conn.close()
        input_n_cat.value = ""
        refrescar_cats()
        mostrar_notificacion("Categoría agregada", C_GREEN)

    vista_ajustes = ft.Container(
        expand=True, bgcolor=C_BG, padding=20,
        content=ft.Column([
            ft.Container(height=30),
            ft.Text("Ajustes", size=28, weight=ft.FontWeight.BOLD, color=C_TEXT_MAIN),
            ft.Text("Administra tus categorías", color=C_TEXT_SEC),
            ft.Container(height=20),
            ft.Row([tipo_n_cat, input_n_cat]),
            ft.ElevatedButton("Agregar Categoría", bgcolor=C_PURPLE, color="#FFFFFF", width=float('inf'), height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)), on_click=agregar_cat),
            ft.Container(height=20),
            ft.Text("Categorías Actuales", weight=ft.FontWeight.BOLD, color=C_TEXT_MAIN),
            ft.Container(content=lista_categorias, expand=True)
        ])
    )

    # --- NAVEGACIÓN Y ENRUTAMIENTO NATIVO (Resuelve el botón de atrás de Android) ---
    nav_bar = ft.NavigationBar(
        bgcolor=C_BG, selected_index=0,
        destinations=[
            ft.NavigationBarDestination(icon=ft.icons.HOME_OUTLINED, selected_icon=ft.icons.HOME, label="Inicio"),
            ft.NavigationBarDestination(icon=ft.icons.SETTINGS_OUTLINED, selected_icon=ft.icons.SETTINGS, label="Ajustes"),
        ],
        on_change=lambda e: cambiar_tab(e.control.selected_index)
    )

    fab = ft.FloatingActionButton(icon=ft.icons.ADD, bgcolor=C_BLUE, shape=ft.RoundedRectangleBorder(radius=15), on_click=lambda e: page.go("/registro"))

    # Contenedor base para intercambiar Inicio y Ajustes
    contenedor_base = ft.Stack([vista_dashboard, vista_ajustes], expand=True)
    
    def cambiar_tab(index):
        vista_dashboard.visible = (index == 0)
        vista_ajustes.visible = (index == 1)
        page.update()

    def route_change(route):
        registrar_actividad()
        page.views.clear()
        
        # Siempre ponemos la base al fondo (Dashboard + Ajustes)
        page.views.append(
            ft.View(
                "/",
                [ft.SafeArea(contenedor_base, expand=True)],
                navigation_bar=nav_bar,
                floating_action_button=fab,
                padding=0, bgcolor=C_BG
            )
        )
        
        # Si la ruta es Bienvenida, la ponemos encima
        if page.route == "/welcome":
            page.views.append(ft.View("/welcome", [ft.SafeArea(vista_bienvenida, expand=True)], padding=0, bgcolor=C_BG))
        
        # Si la ruta es Registro, la ponemos encima
        elif page.route == "/registro":
            page.views.append(ft.View("/registro", [ft.SafeArea(vista_registro, expand=True)], padding=0, bgcolor=C_BG))
            
        page.update()

    def view_pop(view):
        page.views.pop()
        page.go(page.views[-1].route)

    page.on_route_change = route_change
    page.on_view_pop = view_pop # ESTO HACE QUE EL BOTÓN ATRÁS DE ANDROID FUNCIONE BIEN

    # --- INICIO DE APP (Lógica de los 5 minutos) ---
    actualizar_dashboard()
    cargar_historial()
    refrescar_cats()
    cambiar_tab(0)
    
    ultimo_uso = page.client_storage.get("last_active") or 0
    tiempo_actual = time.time()
    
    # 300 segundos = 5 minutos. Si pasó menos de ese tiempo, se salta el welcome
    if (tiempo_actual - ultimo_uso) < 300:
        page.go("/")
    else:
        page.go("/welcome")

ft.app(target=main)
