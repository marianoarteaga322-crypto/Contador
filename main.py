import flet as ft
import sqlite3
import datetime
import os

def main(page: ft.Page):
    # Configuración base de la ventana
    page.title = "Control Financiero"
    page.bgcolor = "#0F172A" # Dark theme moderno (Slate 900)
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.window_width = 400
    page.window_height = 800

    # --- RUTAS SEGURAS ANDROID ---
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
        cursor.execute("SELECT COUNT(*) FROM categorias")
        if cursor.fetchone()[0] == 0:
            default_cats = [
                ("Ingreso", "Repartos App"),
                ("Ingreso", "Propinas"),
                ("Ingreso", "Otros Ingresos"),
                ("Gasto", "Gasolina"),
                ("Gasto", "Mantenimiento"),
                ("Gasto", "Comida en ruta"),
                ("Gasto", "Otros Gastos")
            ]
            cursor.executemany("INSERT INTO categorias (tipo, nombre) VALUES (?, ?)", default_cats)
        conn.commit()
        conn.close()

    init_db()

    # --- VARIABLES DE ESTADO VISUAL ---
    txt_ganancia_neta = ft.Text("$0.00", size=36, weight=ft.FontWeight.BOLD, color="#10B981") # Emerald 500
    txt_ingresos = ft.Text("$0.00", size=16, color="#E2E8F0", weight=ft.FontWeight.W_500)
    txt_gastos = ft.Text("$0.00", size=16, color="#F87171", weight=ft.FontWeight.W_500)
    txt_impuestos = ft.Text("$0.00", size=16, color="#FBBF24", weight=ft.FontWeight.W_500)

    # --- FUNCIONES DE BASE DE DATOS Y UI ---
    def obtener_categorias(tipo_cat):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT nombre FROM categorias WHERE tipo = ?", (tipo_cat,))
        cats = [row[0] for row in cursor.fetchall()]
        conn.close()
        return cats

    def actualizar_dashboard():
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(monto_total), SUM(gastos), SUM(isr + iva), SUM(ganancia_neta) FROM movimientos")
        res = cursor.fetchone()
        conn.close()

        t_ing = res[0] or 0.0
        t_gas = res[1] or 0.0
        t_imp = res[2] or 0.0
        t_net = res[3] or 0.0

        txt_ingresos.value = f"${t_ing:,.2f}"
        txt_gastos.value = f"${t_gas:,.2f}"
        txt_impuestos.value = f"${t_imp:,.2f}"
        txt_ganancia_neta.value = f"${t_net:,.2f}"
        page.update()

    lista_historial = ft.ListView(expand=True, spacing=10, padding=10)

    def borrar_movimiento(mov_id):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM movimientos WHERE id = ?", (mov_id,))
        conn.commit()
        conn.close()
        
        actualizar_dashboard()
        cargar_historial()
        
        page.snack_bar = ft.SnackBar(ft.Text("Registro eliminado correctamente"), bgcolor="#EF4444")
        page.snack_bar.open = True
        page.update()

    def cargar_historial():
        lista_historial.controls.clear()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Seleccionamos id para poder borrarlo después
        cursor.execute("SELECT id, fecha, categoria, monto_total, ganancia_neta FROM movimientos ORDER BY id DESC LIMIT 30")
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            lista_historial.controls.append(
                ft.Container(
                    content=ft.Text("No hay registros recientes.", color="#64748B", text_align=ft.TextAlign.CENTER),
                    padding=20, alignment=ft.alignment.center
                )
            )

        for row in rows:
            mov_id, fecha, categoria, total, neta = row
            lista_historial.controls.append(
                ft.Card(
                    color="#1E293B",
                    elevation=2,
                    content=ft.ListTile(
                        leading=ft.Icon(ft.icons.ACCOUNT_BALANCE_WALLET, color="#34D399", size=30),
                        title=ft.Text(f"Libre: ${neta:,.2f}", weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                        subtitle=ft.Text(f"{fecha} • {categoria} • Total: ${total:,.2f}", color="#94A3B8"),
                        trailing=ft.IconButton(
                            icon=ft.icons.DELETE_OUTLINE, 
                            icon_color="#EF4444",
                            tooltip="Eliminar registro",
                            on_click=lambda e, m_id=mov_id: borrar_movimiento(m_id)
                        )
                    )
                )
            )
        page.update()

    # --- VISTA 1: INICIO (DASHBOARD) ---
    tarjeta_resumen = ft.Card(
        color="#1E293B",
        elevation=4,
        margin=ft.margin.all(15),
        content=ft.Container(
            padding=20,
            content=ft.Column([
                ft.Text("GANANCIA NETA TOTAL", size=12, color="#94A3B8", weight=ft.FontWeight.BOLD),
                txt_ganancia_neta,
                ft.Divider(color="#334155", height=20),
                ft.Row([
                    ft.Column([ft.Text("Ingresos", size=12, color="#94A3B8"), txt_ingresos], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Column([ft.Text("Gastos", size=12, color="#94A3B8"), txt_gastos], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Column([ft.Text("Impuestos", size=12, color="#94A3B8"), txt_impuestos], alignment=ft.MainAxisAlignment.CENTER),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )
    )

    vista_inicio = ft.Column([
        tarjeta_resumen,
        ft.Container(
            content=ft.Text("HISTORIAL DE MOVIMIENTOS", size=14, weight=ft.FontWeight.BOLD, color="#F8FAFC"),
            padding=ft.padding.only(left=20, top=10, bottom=5)
        ),
        lista_historial
    ], expand=True)

    # --- VISTA 2: REGISTRAR ---
    input_ingreso_total = ft.TextField(label="Ganancia Bruta del Día ($)", prefix_text="$ ", keyboard_type=ft.KeyboardType.NUMBER, bgcolor="#1E293B", border_color="#334155")
    input_efectivo = ft.TextField(label="Efectivo Recibido ($)", prefix_text="$ ", keyboard_type=ft.KeyboardType.NUMBER, bgcolor="#1E293B", border_color="#334155")
    input_gastos_op = ft.TextField(label="Gastos Operativos (Gasolina, etc.)", prefix_text="$ ", value="0", keyboard_type=ft.KeyboardType.NUMBER, bgcolor="#1E293B", border_color="#334155")
    
    cat_dropdown = ft.Dropdown(
        label="Categoría del Ingreso",
        options=[ft.dropdown.Option(c) for c in obtener_categorias("Ingreso")],
        value="Repartos App",
        bgcolor="#1E293B",
        border_color="#334155"
    )

    def guardar_cierre(e):
        try:
            monto_total = float(input_ingreso_total.value or 0)
            efectivo = float(input_efectivo.value or 0)
            gastos = float(input_gastos_op.value or 0)
        except ValueError:
            page.snack_bar = ft.SnackBar(ft.Text("Ingresa montos numéricos válidos", color="#FFFFFF"), bgcolor="#EF4444")
            page.snack_bar.open = True
            page.update()
            return

        base_impuestos = monto_total + efectivo
        isr = base_impuestos * 0.021
        iva = base_impuestos * 0.08
        ganancia_neta = monto_total - gastos - (isr + iva)
        fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO movimientos (fecha, tipo, categoria, monto_total, efectivo, isr, iva, gastos, ganancia_neta)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (fecha_actual, "Ingreso", cat_dropdown.value, monto_total, efectivo, isr, iva, gastos, ganancia_neta))
        conn.commit()
        conn.close()

        # Limpiar formulario
        input_ingreso_total.value = ""
        input_efectivo.value = ""
        input_gastos_op.value = "0"
        
        actualizar_dashboard()
        cargar_historial()

        page.snack_bar = ft.SnackBar(ft.Text("¡Jornada registrada exitosamente!", color="#FFFFFF"), bgcolor="#10B981")
        page.snack_bar.open = True
        
        # Volver automáticamente a la pestaña de inicio al guardar
        page.navigation_bar.selected_index = 0
        cambiar_vista(None)

    btn_guardar = ft.ElevatedButton(
        content=ft.Row([ft.Icon(ft.icons.SAVE), ft.Text("Guardar Cierre de Día", size=16, weight=ft.FontWeight.BOLD)], alignment=ft.MainAxisAlignment.CENTER),
        bgcolor="#2563EB", color="#FFFFFF", width=float('inf'), height=50,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
        on_click=guardar_cierre
    )

    vista_registrar = ft.Container(
        padding=20,
        content=ft.Column([
            ft.Text("Nuevo Registro", size=24, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
            ft.Text("Ingresa los datos de tu jornada para calcular retenciones automáticas.", color="#94A3B8", size=14),
            ft.Divider(height=20, color="transparent"),
            input_ingreso_total,
            input_efectivo,
            input_gastos_op,
            cat_dropdown,
            ft.Divider(height=20, color="transparent"),
            btn_guardar
        ], scroll=ft.ScrollMode.AUTO)
    )

    # --- VISTA 3: AJUSTES / CATEGORÍAS ---
    input_nueva_cat = ft.TextField(label="Nombre de categoría", expand=True, bgcolor="#1E293B", border_color="#334155")
    tipo_cat_dropdown = ft.Dropdown(
        options=[ft.dropdown.Option("Ingreso"), ft.dropdown.Option("Gasto")],
        value="Ingreso", width=110, bgcolor="#1E293B", border_color="#334155"
    )
    lista_cats_ui = ft.ListView(expand=True, spacing=5)

    def refrescar_lista_categorias():
        lista_cats_ui.controls.clear()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, tipo, nombre FROM categorias")
        rows = cursor.fetchall()
        conn.close()
        
        for r in rows:
            icon_color = "#34D399" if r[1] == "Ingreso" else "#F87171"
            icon_type = ft.icons.ARROW_UPWARD if r[1] == "Ingreso" else ft.icons.ARROW_DOWNWARD
            
            lista_cats_ui.controls.append(
                ft.ListTile(
                    leading=ft.Icon(icon_type, color=icon_color),
                    title=ft.Text(r[2], color="#F8FAFC"),
                    subtitle=ft.Text(r[1], color="#64748B"),
                    trailing=ft.IconButton(
                        icon=ft.icons.DELETE, 
                        icon_color="#EF4444", 
                        on_click=lambda e, cid=r[0]: borrar_categoria(cid)
                    )
                )
            )
        
        # ACTUALIZAR EL DROPDOWN DE REGISTRO DINÁMICAMENTE
        cat_dropdown.options = [ft.dropdown.Option(c) for c in obtener_categorias("Ingreso")]
        page.update()

    def borrar_categoria(cid):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM categorias WHERE id = ?", (cid,))
        conn.commit()
        conn.close()
        refrescar_lista_categorias()

    def agregar_categoria_nueva(e):
        nombre = input_nueva_cat.value.strip()
        tipo = tipo_cat_dropdown.value
        if not nombre: return
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO categorias (tipo, nombre) VALUES (?, ?)", (tipo, nombre))
        conn.commit()
        conn.close()
        
        input_nueva_cat.value = ""
        refrescar_lista_categorias()
        
        page.snack_bar = ft.SnackBar(ft.Text("Categoría añadida", color="#FFFFFF"), bgcolor="#10B981")
        page.snack_bar.open = True
        page.update()

    vista_ajustes = ft.Container(
        padding=20,
        content=ft.Column([
            ft.Text("Configuración", size=24, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
            ft.Text("Administra tus categorías personalizadas", color="#94A3B8", size=14),
            ft.Divider(height=20, color="transparent"),
            ft.Row([tipo_cat_dropdown, input_nueva_cat], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.ElevatedButton("Agregar Categoría", on_click=agregar_categoria_nueva, bgcolor="#10B981", color="#FFFFFF", width=float('inf'), height=45),
            ft.Divider(color="#334155", height=30),
            ft.Text("Tus Categorías", size=16, weight=ft.FontWeight.BOLD, color="#F8FAFC"),
            lista_cats_ui
        ])
    )

    # --- SISTEMA DE NAVEGACIÓN PRINCIPAL ---
    def cambiar_vista(e):
        idx = page.navigation_bar.selected_index
        vista_inicio.visible = (idx == 0)
        vista_registrar.visible = (idx == 1)
        vista_ajustes.visible = (idx == 2)
        page.update()

    page.navigation_bar = ft.NavigationBar(
        bgcolor="#0F172A",
        selected_index=0,
        on_change=cambiar_vista,
        destinations=[
            ft.NavigationBarDestination(icon=ft.icons.HOME_OUTLINED, selected_icon=ft.icons.HOME, label="Inicio"),
            ft.NavigationBarDestination(icon=ft.icons.ADD_CIRCLE_OUTLINE, selected_icon=ft.icons.ADD_CIRCLE, label="Registrar"),
            ft.NavigationBarDestination(icon=ft.icons.SETTINGS_OUTLINED, selected_icon=ft.icons.SETTINGS, label="Ajustes"),
        ]
    )

    # Ocultar vistas secundarias al inicio
    vista_registrar.visible = False
    vista_ajustes.visible = False

    # Agregar contenedor principal a la página
    page.add(
        ft.SafeArea(
            ft.Stack([
                vista_inicio,
                vista_registrar,
                vista_ajustes
            ], expand=True)
        )
    )

    # Carga inicial de datos
    actualizar_dashboard()
    cargar_historial()
    refrescar_lista_categorias()

ft.app(target=main)
