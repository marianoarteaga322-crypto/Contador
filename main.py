import flet as ft
import sqlite3
import datetime
import os

def main(page: ft.Page):
    page.title = "Control Financiero - Repartidor"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.bgcolor = "#0F172A"
    
    try:
        # --- RUTA 100% SEGURA PARA ANDROID ---
        # Tu paquete es com.flet.contador, usamos su memoria interna garantizada
        android_path = "/data/user/0/com.flet.contador/files"
        android_path_alt = "/data/data/com.flet.contador/files"
        
        if os.path.exists(android_path):
            db_path = os.path.join(android_path, "finanzas_repartidor.db")
        elif os.path.exists(android_path_alt):
            db_path = os.path.join(android_path_alt, "finanzas_repartidor.db")
        else:
            # Si por alguna razón lo abres en PC, lo guarda en la misma carpeta
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

        # Componentes Visuales
        txt_ganancia_neta = ft.Text("$0.00", size=30, weight=ft.FontWeight.BOLD, color="#34D399")
        txt_ingresos = ft.Text("Ingresos: $0.00", size=13, color="#9CA3AF")
        txt_gastos = ft.Text("Gastos: $0.00", size=13, color="#F87171")
        txt_impuestos = ft.Text("Impuestos (ISR+IVA): $0.00", size=13, color="#FBBF24")

        input_ingreso_total = ft.TextField(label="Monto Total Repartos ($)", keyboard_type=ft.KeyboardType.NUMBER, width=350, bgcolor="#1E293B", color="#FFFFFF")
        input_efectivo = ft.TextField(label="Efectivo en Mano ($)", keyboard_type=ft.KeyboardType.NUMBER, width=350, bgcolor="#1E293B", color="#FFFFFF")
        input_gastos_op = ft.TextField(label="Gastos del Día ($)", keyboard_type=ft.KeyboardType.NUMBER, value="0", width=350, bgcolor="#1E293B", color="#FFFFFF")

        def obtener_categorias(tipo_cat):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT nombre FROM categorias WHERE tipo = ?", (tipo_cat,))
            cats = [row[0] for row in cursor.fetchall()]
            conn.close()
            return cats

        cat_dropdown = ft.Dropdown(
            label="Categoría Principal",
            options=[ft.dropdown.Option(c) for c in obtener_categorias("Ingreso")],
            value="Repartos App",
            width=350,
            bgcolor="#1E293B"
        )

        lista_historial = ft.ListView(expand=1, spacing=8, padding=10, auto_scroll=True)

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

            txt_ingresos.value = f"Ingresos: ${t_ing:,.2f}"
            txt_gastos.value = f"Gastos: ${t_gas:,.2f}"
            txt_impuestos.value = f"Impuestos: ${t_imp:,.2f}"
            txt_ganancia_neta.value = f"${t_net:,.2f}"
            page.update()

        def cargar_historial():
            lista_historial.controls.clear()
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT fecha, monto_total, efectivo, ganancia_neta FROM movimientos ORDER BY id DESC LIMIT 20")
            rows = cursor.fetchall()
            conn.close()

            for row in rows:
                lista_historial.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text(f"Fecha: {row[0]}", size=12, color="#9CA3AF"),
                                ft.Text(f"Libre: ${row[3]:,.2f}", weight=ft.FontWeight.BOLD, color="#34D399")
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Text(f"Total: ${row[1]:,.2f} | Efectivo: ${row[2]:,.2f}", size=12, color="#E2E8F0")
                        ]),
                        bgcolor="#1E293B", padding=10, border_radius=8
                    )
                )
            page.update()

        def guardar_cierre(e):
            try:
                monto_total = float(input_ingreso_total.value or 0)
                efectivo = float(input_efectivo.value or 0)
                gastos = float(input_gastos_op.value or 0)
            except ValueError:
                page.snack_bar = ft.SnackBar(ft.Text("Por favor ingresa números válidos"))
                page.snack_bar.open = True
                page.update()
                return

            base_impuestos = monto_total + efectivo
            isr = base_impuestos * 0.021
            iva = base_impuestos * 0.08
            ganancia_neta = monto_total - gastos - (isr + iva)
            fecha_actual = datetime.date.today().strftime("%Y-%m-%d")

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO movimientos (fecha, tipo, categoria, monto_total, efectivo, isr, iva, gastos, ganancia_neta)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (fecha_actual, "Cierre de Día", cat_dropdown.value, monto_total, efectivo, isr, iva, gastos, ganancia_neta))
            conn.commit()
            conn.close()

            input_ingreso_total.value = ""
            input_efectivo.value = ""
            input_gastos_op.value = "0"
            actualizar_dashboard()
            cargar_historial()

            page.snack_bar = ft.SnackBar(ft.Text("¡Cierre de día registrado con éxito!"))
            page.snack_bar.open = True
            page.update()

        btn_guardar = ft.ElevatedButton(text="Registrar Cierre de Jornada", on_click=guardar_cierre, bgcolor="#2563EB", color="#FFFFFF", width=350)

        # Configuración de Categorías
        input_nueva_cat = ft.TextField(label="Nueva categoría", width=220, bgcolor="#1E293B", color="#FFFFFF")
        tipo_cat_dropdown = ft.Dropdown(
            label="Tipo",
            options=[ft.dropdown.Option("Ingreso"), ft.dropdown.Option("Gasto")],
            value="Gasto", width=110, bgcolor="#1E293B"
        )
        lista_cats_ui = ft.ListView(expand=1, spacing=5, height=150)

        def refrescar_lista_categorias():
            lista_cats_ui.controls.clear()
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id, tipo, nombre FROM categorias")
            rows = cursor.fetchall()
            conn.close()
            for r in rows:
                lista_cats_ui.controls.append(
                    ft.Row([
                        ft.Text(f"[{r[1]}] {r[2]}", color="#E2E8F0", size=13),
                        ft.IconButton(icon=ft.icons.DELETE, icon_color="#F87171", on_click=lambda e, cid=r[0]: borrar_categoria(cid))
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                )
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
            page.snack_bar = ft.SnackBar(ft.Text("Categoría agregada con éxito"))
            page.snack_bar.open = True
            page.update()

        btn_add_cat = ft.ElevatedButton(text="Agregar", on_click=agregar_categoria_nueva, bgcolor="#10B981", color="#FFFFFF")

        tab_registro = ft.Container(
            content=ft.Column([
                ft.Text("Cierre de Día y Finanzas", size=16, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                input_ingreso_total, input_efectivo, input_gastos_op, cat_dropdown, btn_guardar,
                ft.Divider(color="#374151"),
                ft.Text("Historial Reciente", size=14, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                lista_historial
            ], scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=10
        )

        tab_config = ft.Container(
            content=ft.Column([
                ft.Text("Personalizar Categorías", size=16, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                ft.Row([tipo_cat_dropdown, input_nueva_cat], alignment=ft.MainAxisAlignment.CENTER),
                btn_add_cat,
                ft.Divider(color="#374151"),
                ft.Text("Categorías Actuales:", size=13, color="#9CA3AF"),
                lista_cats_ui
            ], scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=10
        )

        dashboard_header = ft.Container(
            content=ft.Column([
                ft.Text("Ganancia Neta Real (Libre)", size=12, color="#9CA3AF", text_align=ft.TextAlign.CENTER),
                txt_ganancia_neta,
                ft.Row([txt_ingresos, txt_gastos, txt_impuestos], alignment=ft.MainAxisAlignment.SPACE_AROUND),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor="#1E293B", padding=15, border_radius=12, margin=ft.margin.only(bottom=10)
        )

        tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(text="Registrar", icon=ft.icons.EDIT, content=tab_registro),
                ft.Tab(text="Configuración", icon=ft.icons.SETTINGS, content=tab_config),
            ],
            expand=1
        )

        page.add(
            ft.Container(
                content=ft.Column([
                    dashboard_header,
                    tabs
                ]),
                padding=15, bgcolor="#0F172A", expand=True
            )
        )

        actualizar_dashboard()
        cargar_historial()
        refrescar_lista_categorias()

    except Exception as ex:
        page.clean()
        page.add(ft.Text(f"Error crítico al iniciar:\n{str(ex)}", color="red", size=14))
        page.update()

ft.app(target=main)
