from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.signing import Signer, BadSignature
from django.http import HttpResponse, JsonResponse
from .models import Users, UsersInfo, Products, Stores, Category, Sales, SalesBag, SalesMovement, SuperAdmin
import random
from django.db import connection
from django.db.models import Q, Sum
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import base64
import bcrypt

# Inicializar signer para cookies seguras
signer = Signer()

# =====================================================
# FUNCIONES AUXILIARES PARA HASHEO DE CONTRASEÑAS
# =====================================================

def hash_password(password):
    """Hashea una contraseña usando bcrypt"""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(password, hashed_password):
    """Verifica si una contraseña coincide con su hash"""
    try:
        password_bytes = password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except (ValueError, AttributeError):
        # Si falla (contraseña no hasheada o inválida), retornar False
        return False

# Función auxiliar para leer cookie firmada
def _get_user_from_cookie(request):
    """Lee y verifica la cookie firmada del user_id"""
    signed_user_id = request.COOKIES.get('user_id')
    if signed_user_id:
        try:
            # Verificar firma y devolver valor original
            return signer.unsign(signed_user_id)
        except BadSignature:
            # Cookie manipulada o inválida
            return None
    return None

# Función auxiliar para registrar movimientos
def _registrar_movimiento(user_id, type_movement, type_action, id_sale=None, id_product=None):
    """
    Registra un movimiento en la tabla sales_movement
    
    Args:
        user_id: UUID del usuario que realiza la acción
        type_movement: 'venta' o 'producto'
        type_action: 'creacion', 'modificacion' o 'eliminacion'
        id_sale: UUID de la venta (opcional, solo si type_movement='venta')
        id_product: UUID del producto (opcional, solo si type_movement='producto')
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO sales_movement 
                (type_movement, type_action, date_movement, id_sale, id_product, id_user)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, [
                type_movement,
                type_action,
                datetime.now(),
                id_sale,
                id_product,
                user_id
            ])
    except Exception as e:
        print(f"Error al registrar movimiento: {str(e)}")
        # No lanzamos excepción para no interrumpir el flujo principal

# Create your views here.
def index(request):
    # Redirigir al dashboard si está autenticado
    user_id = request.session.get('user_id') or _get_user_from_cookie(request)
    
    if not user_id:
        return redirect('login')
    
    return redirect('dashboard')

def click_me_target(request):
    # Verificar autenticación (sesión O cookie)
    user_id = request.session.get('user_id') or _get_user_from_cookie(request)
    
    if not user_id:
        return redirect('login')
    
    return render(request, 'core/partials/clicked_content.html')

def login_view(request):
    # Si ya está autenticado, redirigir según el tipo de usuario
    if 'user_id' in request.session:
        if request.session.get('is_superadmin'):
            return redirect('superusuario')
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Primero verificar si es SuperAdmin
        try:
            superadmin = SuperAdmin.objects.get(username=username)
            
            # Verificar contraseña hasheada
            if verify_password(password, superadmin.password):
                # Guardar en sesión como superadmin
                request.session['username'] = superadmin.username
                request.session['is_superadmin'] = True
                request.session['user_name'] = 'SuperAdministrador'
                
                messages.success(request, f'¡Bienvenido SuperAdministrador!')
                
                # Crear respuesta y redirigir al panel de superusuario
                response = redirect('superusuario')
                
                # Cookie firmada con el username
                signed_username = signer.sign(superadmin.username)
                response.set_cookie(
                    'superadmin_id',
                    signed_username,
                    max_age=30*24*60*60,
                    httponly=True,
                    secure=False,
                    samesite='Lax'
                )
                
                return response
            
        except SuperAdmin.DoesNotExist:
            pass  # No es superadmin, intentar con usuario normal
        
        # Verificar si es usuario normal
        try:
            # Buscar usuario por username
            user = Users.objects.only('id_user', 'id_store', 'password', 'state_user', 'username', 'type_user').get(username=username)
            
            # Verificar contraseña hasheada
            if not verify_password(password, user.password):
                messages.error(request, 'Usuario o contraseña incorrectos')
                return render(request, 'core/login.html')
            
            # Verificar si el usuario está activo
            if not user.state_user:
                messages.error(request, 'Tu cuenta está desactivada. Contacta al administrador.')
                return render(request, 'core/login.html')
            
            # Guardar en sesión (incluyendo id_store)
            request.session['user_id'] = str(user.id_user)
            request.session['username'] = user.username
            request.session['is_admin'] = user.type_user
            request.session['is_superadmin'] = False
            request.session['id_store'] = str(user.id_store_id) if user.id_store_id else None
            
            # Obtener nombre completo si existe (solo campo necesario)
            try:
                user_info = UsersInfo.objects.only('name').get(id_user=user)
                request.session['user_name'] = user_info.name
            except UsersInfo.DoesNotExist:
                request.session['user_name'] = username
            
            messages.success(request, f'¡Bienvenido {request.session["user_name"]}!')
            
            # Redirigir a dashboard normal
            response = redirect('dashboard')
            
            # Cookie firmada con el user_id (válida por 30 días)
            signed_user_id = signer.sign(str(user.id_user))
            response.set_cookie(
                'user_id',
                signed_user_id,
                max_age=30*24*60*60,  # 30 días en segundos
                httponly=True,         # No accesible desde JavaScript (seguridad XSS)
                secure=False,          # Cambia a True en producción (requiere HTTPS)
                samesite='Lax'         # Protección CSRF
            )
            
            return response
            
        except Users.DoesNotExist:
            messages.error(request, 'Usuario o contraseña incorrectos')
    
    return render(request, 'core/login.html')

# =====================================================
# FUNCIONES AUXILIARES PARA GRÁFICOS
# =====================================================
# FUNCIONES AUXILIARES PARA GRÁFICOS CON PLOTLY
# =====================================================

def grafico_stock_productos(user_store):
    """Genera gráfico de barras vertical de stock por producto con Plotly"""
    try:
        # Obtener TODOS los productos con su stock (sin límite)
        productos = Products.objects.filter(
            id_store=user_store,
            status_product=True
        ).values('name', 'stock').order_by('name')  # Ordenar alfabéticamente
        
        if not productos or len(list(productos)) == 0:
            # Gráfico vacío con mensaje
            fig = go.Figure()
            fig.add_annotation(
                text="No hay productos<br>en el inventario",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16, color="gray")
            )
            fig.update_layout(
                xaxis=dict(visible=False),
                yaxis=dict(visible=False),
                height=500,
                plot_bgcolor='white'
            )
        else:
            df = pd.DataFrame(list(productos))
            df['stock'] = df['stock'].astype(float)
            
            # Colores según nivel de stock
            colors = ['#10b981' if stock >= 10 else '#f59e0b' if stock > 0 else '#ef4444' 
                     for stock in df['stock']]
            
            # Calcular ancho dinámico basado en cantidad de productos
            num_productos = len(df)
            ancho_minimo_por_barra = 80  # píxeles por barra
            ancho_calculado = max(1600, num_productos * ancho_minimo_por_barra)
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df['name'],  # Productos en eje X
                y=df['stock'],  # Stock en eje Y
                marker=dict(color=colors, line=dict(color='white', width=2)),
                text=df['stock'].astype(int),
                textposition='outside',
                textfont=dict(size=12, color='black'),
                hovertemplate='<b>%{x}</b><br>Stock: %{y}<extra></extra>'
            ))
            
            fig.update_layout(
                title=dict(
                    text='Stock por Producto',
                    font=dict(size=18, color='#111827', family='Arial, sans-serif'),
                    x=0.5,
                    xanchor='center'
                ),
                xaxis=dict(
                    title=dict(text='Producto', font=dict(size=14, color='#374151')),
                    tickangle=-45,  # Rotar etiquetas para mejor lectura
                    gridcolor='#E5E7EB',
                    showgrid=False
                ),
                yaxis=dict(
                    title=dict(text='Stock Disponible', font=dict(size=14, color='#374151')),
                    gridcolor='#E5E7EB',
                    showgrid=True,
                    rangemode='tozero'
                ),
                plot_bgcolor='white',
                paper_bgcolor='white',
                height=700,
                width=ancho_calculado,  # Ancho dinámico
                autosize=False,
                margin=dict(l=80, r=20, t=80, b=150),  # Más margen abajo para etiquetas rotadas
                hovermode='closest'
            )
        
        return fig.to_html(full_html=False, include_plotlyjs='cdn', config={'displayModeBar': False, 'responsive': True})
    
    except Exception as e:
        print(f"❌ Error generando gráfico de stock: {e}")
        import traceback
        traceback.print_exc()
        
        # Gráfico de error
        fig = go.Figure()
        fig.add_annotation(
            text=f"Error al generar gráfico<br>{str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color="red")
        )
        fig.update_layout(
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            height=500,
            plot_bgcolor='white'
        )
        return fig.to_html(full_html=False, include_plotlyjs='cdn', config={'displayModeBar': False})

def grafico_precio_ventas_producto(user_store):
    """Genera gráfico de barras: producto vs ganancia"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    p.name,
                    SUM((p.price_sale - p.price_buy) * sb.quantitity) as ganancia_total
                FROM sales_bag sb
                INNER JOIN products p ON sb.id_product = p.id_product
                INNER JOIN sales s ON sb.id_sale = s.id_sale
                WHERE s.id_store = %s AND s.state = true
                GROUP BY p.id_product, p.name
                ORDER BY ganancia_total DESC
            """, [str(user_store.id_store)])
            
            rows = cursor.fetchall()
        
        fig = go.Figure()
        
        if not rows or len(rows) == 0:
            # Estado vacío
            fig.add_annotation(
                text="No hay datos de ventas<br>para mostrar",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16, color="gray"),
                bgcolor="white",
                bordercolor="gray",
                borderwidth=2,
                borderpad=10
            )
            fig.update_layout(
                xaxis=dict(visible=False),
                yaxis=dict(visible=False),
                height=700,
                plot_bgcolor='white'
            )
        else:
            df = pd.DataFrame(rows, columns=['Producto', 'Ganancia'])
            df['Ganancia'] = df['Ganancia'].astype(float)
            
            # Calcular ancho dinámico basado en la cantidad de productos
            num_productos = len(df)
            ancho_dinamico = max(1600, num_productos * 80)  # Mínimo 1600px, 80px por producto
            
            # Colores: verde para ganancia positiva, rojo para negativa
            colors = ['#10b981' if g >= 0 else '#ef4444' for g in df['Ganancia']]
            
            fig.add_trace(go.Bar(
                x=df['Producto'],
                y=df['Ganancia'],
                marker=dict(
                    color=colors,
                    line=dict(color='white', width=2)
                ),
                text=[f'${g:,.0f}' for g in df['Ganancia']],
                textposition='outside',
                textfont=dict(size=12, color='black'),
                hovertemplate='<b>%{x}</b><br>Ganancia: $%{y:,.0f}<extra></extra>'
            ))
        
        fig.update_layout(
            title=dict(
                text=f'Productos por Ganancia ({num_productos} productos)',
                font=dict(size=18, color='#111827', family='Arial, sans-serif'),
                x=0.5,
                xanchor='center',
                y=0.98
            ),
            xaxis=dict(
                title=dict(text='Producto', font=dict(size=14, color='#374151')),
                tickangle=-45,
                gridcolor='#E5E7EB',
                showgrid=False
            ),
            yaxis=dict(
                title=dict(text='Ganancia Total ($)', font=dict(size=14, color='#374151')),
                gridcolor='#E5E7EB',
                showgrid=True,
                tickformat='$,.0f'
            ),
            hovermode='x unified',
            height=700,
            width=ancho_dinamico,
            autosize=False,
            plot_bgcolor='white',
            paper_bgcolor='white',
            margin=dict(l=80, r=20, t=80, b=150)
        )
        
        return fig.to_html(full_html=False, include_plotlyjs='cdn', config={'displayModeBar': False, 'responsive': True})
        
    except Exception as e:
        print(f"❌ Error generando gráfico precio-ventas: {e}")
        import traceback
        traceback.print_exc()
        # Retornar figura de error
        fig = go.Figure()
        fig.add_annotation(
            text=f"Error al generar gráfico<br>{str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color="red")
        )
        fig.update_layout(height=500, plot_bgcolor='white')
        return fig.to_html(full_html=False, include_plotlyjs='cdn', config={'displayModeBar': False})

def grafico_historial_ganancias(user_store):
    """Genera gráfico de línea del historial de ganancias en el tiempo"""
    try:
        # Obtener ventas agrupadas por fecha
        ventas = Sales.objects.filter(
            id_store=user_store,
            state=True
        ).values('date_sale').annotate(
            ganancia_dia=Sum('total')
        ).order_by('date_sale')
        
        fig = go.Figure()
        
        if not ventas or len(list(ventas)) == 0:
            # Estado vacío
            fig.add_annotation(
                text="No hay historial de ventas<br>para mostrar",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16, color="gray"),
                bgcolor="white",
                bordercolor="gray",
                borderwidth=2,
                borderpad=10
            )
        else:
            df = pd.DataFrame(list(ventas))
            df['date_sale'] = pd.to_datetime(df['date_sale'])
            # Convertir a float para evitar problemas con Decimal
            df['ganancia_dia'] = df['ganancia_dia'].astype(float)
            
            # Calcular ganancia acumulada
            df['ganancia_acumulada'] = df['ganancia_dia'].cumsum()
            
            # Línea 1: Ganancia Acumulada (área sombreada)
            fig.add_trace(go.Scatter(
                x=df['date_sale'],
                y=df['ganancia_acumulada'],
                mode='lines+markers',
                name='Ganancia Acumulada',
                line=dict(color='#8b5cf6', width=3),
                marker=dict(size=8, color='#8b5cf6', line=dict(color='white', width=2)),
                fill='tozeroy',
                fillcolor='rgba(139, 92, 246, 0.15)',
                hovertemplate='<b>%{x|%Y-%m-%d}</b><br>Acumulada: $%{y:,.2f}<extra></extra>'
            ))
            
            # Línea 2: Ganancia por día (siempre será menor que la acumulada)
            fig.add_trace(go.Scatter(
                x=df['date_sale'],
                y=df['ganancia_dia'],
                mode='lines+markers',
                name='Ganancia del Día',
                line=dict(color='#10b981', width=2.5),
                marker=dict(size=7, color='#10b981', line=dict(color='white', width=1.5)),
                fill='tozeroy',
                fillcolor='rgba(16, 185, 129, 0.15)',
                hovertemplate='<b>%{x|%Y-%m-%d}</b><br>Del día: $%{y:,.2f}<extra></extra>'
            ))
        
        # Configurar diseño con un solo eje Y
        fig.update_layout(
            title=dict(text='Historial de Ganancias en el Tiempo', font=dict(size=16, family='Arial Black'), y=0.98),
            xaxis=dict(title='Fecha', tickangle=45),
            yaxis=dict(
                title='Ganancias ($)', 
                tickformat='$,.0f',
                side='left'
            ),
            hovermode='x unified',
            height=700,
            width=1600,
            autosize=False,
            plot_bgcolor='white',
            paper_bgcolor='white',
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="left", x=0),
            margin=dict(l=60, r=60, t=80, b=150)
        )
        
        return fig.to_html(full_html=False, include_plotlyjs='cdn', config={'displayModeBar': False, 'responsive': True})
        
    except Exception as e:
        print(f"❌ Error generando gráfico de ganancias: {e}")
        import traceback
        traceback.print_exc()
        # Retornar figura de error
        fig = go.Figure()
        fig.add_annotation(
            text=f"Error al generar gráfico<br>{str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color="red")
        )
        fig.update_layout(height=500, plot_bgcolor='white')
        return fig.to_html(full_html=False, include_plotlyjs='cdn', config={'displayModeBar': False})

def grafico_ventas_producto_por_fecha():
    """Genera gráfico de línea vacío que se llenará con JavaScript"""
    fig = go.Figure()
    
    fig.add_annotation(
        text="Selecciona un producto del menú desplegable<br>para ver su historial de ventas",
        xref="paper", yref="paper",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=16, color="gray"),
        bgcolor="white",
        bordercolor="gray",
        borderwidth=2,
        borderpad=10
    )
    
    fig.update_layout(
        title=dict(
            text='Ventas por Fecha - Selecciona un Producto',
            font=dict(size=18, color='#111827', family='Arial, sans-serif'),
            x=0.5,
            xanchor='center'
        ),
        xaxis=dict(
            title=dict(text='Fecha', font=dict(size=14, color='#374151')),
            gridcolor='#E5E7EB',
            showgrid=True
        ),
        yaxis=dict(
            title=dict(text='Cantidad Vendida', font=dict(size=14, color='#374151')),
            gridcolor='#E5E7EB',
            showgrid=True
        ),
        height=700,
        width=1600,
        autosize=False,
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(l=80, r=20, t=80, b=80)
    )
    
    return fig.to_html(full_html=False, include_plotlyjs='cdn', config={'displayModeBar': False, 'responsive': True}, div_id='grafico_ventas_producto')

# =====================================================
# FIN FUNCIONES AUXILIARES PARA GRÁFICOS
# =====================================================

def logout_view(request):
    # Limpiar toda la sesión
    request.session.flush()
    
    # Crear respuesta y eliminar cookies
    response = redirect('login')
    response.delete_cookie('user_id')
    response.delete_cookie('superadmin_id')
    
    messages.info(request, 'Has cerrado sesión correctamente')
    return response

# Vistas del dashboard
def dashboard_view(request):
    # Verificar autenticación
    user_id = request.session.get('user_id') or _get_user_from_cookie(request)
    if not user_id:
        return redirect('login')
    
    # Obtener el usuario y su tienda
    try:
        user = Users.objects.select_related('id_store').get(id_user=user_id)
        user_store = user.id_store
        if not user_store:
            return HttpResponse("Usuario sin tienda asignada", status=400)
    except Users.DoesNotExist:
        return redirect('login')
    
    from django.db.models import Sum, Count, Avg, Q
    from datetime import datetime, timedelta
    
    # === ANÁLISIS DE PRODUCTOS ===
    productos_activos = Products.objects.filter(id_store=user_store, status_product=True).count()
    productos_sin_stock = Products.objects.filter(id_store=user_store, status_product=True, stock=0).count()
    productos_stock_bajo = Products.objects.filter(
        id_store=user_store, 
        status_product=True, 
        stock__gt=0, 
        stock__lt=10
    ).count()
    
    # Valor del inventario (precio de compra * stock)
    valor_inventario = 0
    try:
        productos_con_stock = Products.objects.filter(
            id_store=user_store,
            status_product=True
        )
        for producto in productos_con_stock:
            valor_inventario += (producto.price_buy * producto.stock)
    except Exception as e:
        print(f"Error calculando valor inventario: {e}")
        valor_inventario = 0
    
    # === ANÁLISIS DE VENTAS ===
    # Obtener ventas de la tienda directamente por id_store
    total_ventas = Sales.objects.filter(id_store=user_store).count()
    ventas_activas = Sales.objects.filter(id_store=user_store, state=True).count()
    ventas_canceladas = Sales.objects.filter(id_store=user_store, state=False).count()
    
    ingresos_totales = Sales.objects.filter(
        id_store=user_store, 
        state=True
    ).aggregate(total=Sum('total'))['total'] or 0
    
    # Ventas del mes actual
    hoy = datetime.now()
    primer_dia_mes = hoy.replace(day=1)
    ventas_mes = Sales.objects.filter(
        id_store=user_store,
        state=True,
        date_sale__gte=primer_dia_mes
    ).aggregate(
        total=Sum('total'),
        cantidad=Count('id_sale')
    )
    ingresos_mes = ventas_mes['total'] or 0
    cantidad_ventas_mes = ventas_mes['cantidad'] or 0
    
    # Ventas de la semana
    inicio_semana = hoy - timedelta(days=7)
    ventas_semana = Sales.objects.filter(
        id_store=user_store,
        state=True,
        date_sale__gte=inicio_semana
    ).aggregate(
        total=Sum('total'),
        cantidad=Count('id_sale')
    )
    ingresos_semana = ventas_semana['total'] or 0
    cantidad_ventas_semana = ventas_semana['cantidad'] or 0
    
    # Ventas de hoy
    ventas_hoy = Sales.objects.filter(
        id_store=user_store,
        state=True,
        date_sale=hoy.date()
    ).aggregate(
        total=Sum('total'),
        cantidad=Count('id_sale')
    )
    ingresos_hoy = ventas_hoy['total'] or 0
    cantidad_ventas_hoy = ventas_hoy['cantidad'] or 0
    
    # === ANÁLISIS DE USUARIOS ===
    total_usuarios = Users.objects.filter(id_store=user_store).count()
    usuarios_activos = Users.objects.filter(id_store=user_store, state_user=True).count()
    usuarios_admin = Users.objects.filter(id_store=user_store, type_user=True).count()
    
    # === ANÁLISIS DE CATEGORÍAS ===
    total_categorias = Category.objects.filter(id_store=user_store).count()
    
    # Productos por categoría (Top 5)
    productos_por_categoria = Products.objects.filter(
        id_store=user_store,
        status_product=True
    ).values('category').annotate(
        cantidad=Count('id_product')
    ).order_by('-cantidad')[:5]
    
    # === PRODUCTOS MÁS VENDIDOS ===
    # A través de sales_bag
    productos_mas_vendidos = []
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT p.name, SUM(sb.quantitity) as total_vendido
                FROM sales_bag sb
                INNER JOIN products p ON sb.id_product = p.id_product
                INNER JOIN sales s ON sb.id_sale = s.id_sale
                WHERE s.id_store = %s AND s.state = true
                GROUP BY p.id_product, p.name
                ORDER BY total_vendido DESC
                LIMIT 5
            """, [user_store.id_store])
            
            for row in cursor.fetchall():
                productos_mas_vendidos.append({
                    'nombre': row[0],
                    'cantidad': float(row[1])
                })
    except Exception as e:
        print(f"Error obteniendo productos más vendidos: {e}")
        pass
    
    # === ÚLTIMAS VENTAS ===
    ultimas_ventas = Sales.objects.filter(
        id_store=user_store
    ).order_by('-date_sale')[:5]
    
    # === PRODUCTOS CON STOCK CRÍTICO ===
    productos_criticos = Products.objects.filter(
        id_store=user_store,
        status_product=True,
        stock__lt=10
    ).order_by('stock')[:5]
    
    # Promedio de venta
    promedio_venta = 0
    if cantidad_ventas_mes > 0:
        promedio_venta = ingresos_mes / cantidad_ventas_mes
    
    # Utilidad del mes (suma de utility de ventas completadas del mes)
    utilidad_mes = Sales.objects.filter(
        id_store=user_store,
        state=True,
        date_sale__gte=primer_dia_mes
    ).aggregate(total=Sum('utility'))['total'] or 0
    
    # === GENERAR GRÁFICOS ===
    print("🎨 Generando gráficos...")
    grafico_stock = grafico_stock_productos(user_store)
    grafico_precio_ventas = grafico_precio_ventas_producto(user_store)
    grafico_ganancias = grafico_historial_ganancias(user_store)
    grafico_ventas_por_producto = grafico_ventas_producto_por_fecha()
    print("✅ Gráficos generados")
    
    # Lista de productos para el dropdown
    productos_dropdown = Products.objects.filter(
        id_store=user_store,
        status_product=True
    ).values('id_product', 'name').order_by('name')
    
    context = {
        # Productos
        'productos_activos': productos_activos,
        'productos_sin_stock': productos_sin_stock,
        'productos_stock_bajo': productos_stock_bajo,
        'valor_inventario': valor_inventario,
        
        # Ventas generales
        'total_ventas': total_ventas,
        'ventas_activas': ventas_activas,
        'ventas_canceladas': ventas_canceladas,
        'ingresos_totales': ingresos_totales,
        
        # Ventas por período
        'ingresos_mes': ingresos_mes,
        'cantidad_ventas_mes': cantidad_ventas_mes,
        'ingresos_semana': ingresos_semana,
        'cantidad_ventas_semana': cantidad_ventas_semana,
        'ingresos_hoy': ingresos_hoy,
        'cantidad_ventas_hoy': cantidad_ventas_hoy,
        'promedio_venta': promedio_venta,
        'utilidad_mes': utilidad_mes,
        
        # Usuarios
        'total_usuarios': total_usuarios,
        'usuarios_activos': usuarios_activos,
        'usuarios_admin': usuarios_admin,
        
        # Categorías
        'total_categorias': total_categorias,
        'productos_por_categoria': productos_por_categoria,
        
        # Listas
        'productos_mas_vendidos': productos_mas_vendidos,
        'ultimas_ventas': ultimas_ventas,
        'productos_criticos': productos_criticos,
        
        # Info de tienda
        'nombre_tienda': user_store.name,
        'id_store': str(user_store.id_store),
        
        # Gráficos (base64)
        'grafico_stock': grafico_stock,
        'grafico_precio_ventas': grafico_precio_ventas,
        'grafico_ganancias': grafico_ganancias,
        'grafico_ventas_por_producto': grafico_ventas_por_producto,
        'productos_dropdown': list(productos_dropdown),
    }
    
    return render(request, 'core/dashboard.html', context)

def productos_view(request):
    # Verificar autenticación
    user_id = request.session.get('user_id') or _get_user_from_cookie(request)
    if not user_id:
        return redirect('login')
    
    # Obtener el usuario actual y su tienda
    try:
        user = Users.objects.get(id_user=user_id)
        user_store = user.id_store
        
        if not user_store:
            messages.error(request, 'No tienes una tienda asignada.')
            return redirect('dashboard')
    except Users.DoesNotExist:
        return redirect('login')
    
    # Obtener parámetros de búsqueda y filtrado
    search_query = request.GET.get('search', '').strip()
    category_filter = request.GET.get('category', '').strip()
    
    # Obtener solo productos activos de la tienda del usuario
    productos = Products.objects.select_related('id_store').filter(
        status_product=True,
        id_store=user_store
    )
    
    # Aplicar filtro de búsqueda si existe
    if search_query:
        productos = productos.filter(name__icontains=search_query)
    
    # Aplicar filtro de categoría si existe (filtrar por nombre de categoría en el campo category)
    if category_filter:
        productos = productos.filter(category=category_filter)
    
    # Ordenar por nombre
    productos = productos.order_by('name')
    
    # Obtener solo las categorías de la tienda del usuario
    categorias = Category.objects.filter(id_store=user_store).order_by('name_category')
    
    # Calcular el estado del stock para cada producto
    productos_con_estado = []
    productos_activos = 0
    productos_stock_bajo = 0
    
    for producto in productos:
        stock_num = float(producto.stock)
        
        # Contar productos activos
        productos_activos += 1
        
        if stock_num == 0:
            estado = 'agotado'
            estado_clase = 'bg-red-100 text-red-800'
            estado_texto = 'Agotado'
            productos_stock_bajo += 1
        elif stock_num < 10:
            estado = 'bajo'
            estado_clase = 'bg-yellow-100 text-yellow-800'
            estado_texto = 'Stock Bajo'
            productos_stock_bajo += 1
        else:
            estado = 'disponible'
            estado_clase = 'bg-green-100 text-green-800'
            estado_texto = 'En Stock'
        
        # Convertir imagen a base64 si existe
        imagen_base64 = None
        if producto.image:
            try:
                imagen_base64 = base64.b64encode(producto.image).decode('utf-8')
            except Exception:
                imagen_base64 = None
        
        productos_con_estado.append({
            'producto': producto,
            'imagen_base64': imagen_base64,
            'estado': estado,
            'estado_clase': estado_clase,
            'estado_texto': estado_texto
        })
    
    context = {
        'productos_con_estado': productos_con_estado,
        'total_productos': len(productos_con_estado),
        'productos_activos': productos_activos,
        'productos_stock_bajo': productos_stock_bajo,
        'total_categorias': categorias.count(),
        'categorias': categorias,
        'search_query': search_query,
        'category_filter': category_filter,
    }
    
    return render(request, 'core/productos.html', context)

def ventas_view(request):
    # Verificar autenticación
    user_id = request.session.get('user_id') or _get_user_from_cookie(request)
    if not user_id:
        return redirect('login')
    
    # Obtener el usuario y su tienda
    try:
        user = Users.objects.select_related('id_store').get(id_user=user_id)
        user_store = user.id_store
        if not user_store:
            return HttpResponse("Usuario sin tienda asignada", status=400)
    except Users.DoesNotExist:
        return redirect('login')
    
    # Obtener filtros
    search_id = request.GET.get('search_id', '').strip()
    fecha_inicio = request.GET.get('fecha_inicio', '').strip()
    fecha_fin = request.GET.get('fecha_fin', '').strip()
    estado = request.GET.get('estado', '').strip()
    
    # Obtener ventas de la tienda directamente por id_store
    ventas = Sales.objects.filter(id_store=user_store).order_by('-date_sale')
    
    # Aplicar filtros
    if search_id:
        ventas = ventas.filter(id_sale__icontains=search_id)
    
    if fecha_inicio:
        ventas = ventas.filter(date_sale__gte=fecha_inicio)
    
    if fecha_fin:
        ventas = ventas.filter(date_sale__lte=fecha_fin)
    
    if estado:
        estado_bool = estado == 'true'
        ventas = ventas.filter(state=estado_bool)
    
    # Calcular estadísticas solo de la tienda del usuario
    from django.db.models import Sum
    total_ventas = Sales.objects.filter(id_store=user_store).count()
    ventas_activas = Sales.objects.filter(id_store=user_store, state=True).count()
    ventas_canceladas = Sales.objects.filter(id_store=user_store, state=False).count()
    total_ingresos = Sales.objects.filter(id_store=user_store, state=True).aggregate(Sum('total'))['total__sum'] or 0
    
    context = {
        'ventas': ventas,
        'total_ventas': total_ventas,
        'ventas_activas': ventas_activas,
        'ventas_canceladas': ventas_canceladas,
        'total_ingresos': total_ingresos,
        'search_id': search_id,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'estado': estado,
        'resultados_filtrados': ventas.count(),
    }
    
    return render(request, 'core/ventas.html', context)

def crear_venta_view(request):
    # Verificar autenticación
    user_id = request.session.get('user_id') or _get_user_from_cookie(request)
    if not user_id:
        return redirect('login')
    
    # Obtener el id_store del usuario autenticado
    try:
        usuario_actual = Users.objects.get(id_user=user_id)
        id_store_actual = usuario_actual.id_store_id
    except Users.DoesNotExist:
        messages.error(request, 'No se pudo obtener la información de tu tienda')
        return redirect('dashboard')
    
    if request.method == 'GET':
        # Obtener productos disponibles de la tienda
        productos = Products.objects.filter(id_store_id=id_store_actual, status_product=True, stock__gt=0).order_by('name')
        
        context = {
            'productos': productos
        }
        return render(request, 'core/crear_venta.html', context)
    
    elif request.method == 'POST':
        import json
        from datetime import datetime
        
        try:
            # Obtener datos del formulario
            productos_json = request.POST.get('productos', '[]')
            productos_venta = json.loads(productos_json)
            metodo_pago = request.POST.get('metodo_pago', '').strip()
            
            if not productos_venta:
                messages.error(request, 'Debes agregar al menos un producto a la venta')
                return redirect('crear_venta')
            
            if not metodo_pago:
                messages.error(request, 'Debes seleccionar un método de pago')
                return redirect('crear_venta')
            
            # Calcular total e items
            total_venta = 0
            total_items = 0
            for item in productos_venta:
                total_venta += float(item['subtotal'])
                total_items += int(item['quantity'])
            
            # Crear la venta con SQL directo (solo campos que existen en la tabla)
            with connection.cursor() as cursor:
                # Insertar venta - campos: date_sale, items, total, pay_method, state
                cursor.execute("""
                    INSERT INTO sales (date_sale, items, total, pay_method, state) 
                    VALUES (%s, %s, %s, %s, %s) 
                    RETURNING id_sale
                """, [datetime.now().date(), total_items, total_venta, metodo_pago, True])
                
                id_sale_generado = cursor.fetchone()[0]
                
                # Insertar productos en sales_bag y actualizar stock
                for item in productos_venta:
                    producto_id = item['id_product']
                    cantidad = int(item['quantity'])
                    
                    # Insertar en sales_bag
                    cursor.execute("""
                        INSERT INTO sales_bag (id_sale, id_product, quantitity) 
                        VALUES (%s, %s, %s)
                    """, [id_sale_generado, producto_id, cantidad])
                    
                    # Actualizar stock del producto
                    cursor.execute("""
                        UPDATE products 
                        SET stock = stock - %s 
                        WHERE id_product = %s
                        RETURNING stock, name, id_store
                    """, [cantidad, producto_id])
                    
                    # Obtener el stock actualizado y verificar si está bajo
                    resultado = cursor.fetchone()
                    if resultado:
                        nuevo_stock = float(resultado[0])
                        nombre_producto = resultado[1]
                        id_store = resultado[2]
                        
                        # Si el stock quedó bajo (menos de 10), enviar alerta
                        if nuevo_stock < 10:
                            from threading import Thread
                            from .notifications import enviar_alerta_stock_bajo
                            import time
                            
                            # Obtener el email del usuario logueado
                            try:
                                user_info = UsersInfo.objects.get(id_user=user_id)
                                user_email = user_info.email
                            except UsersInfo.DoesNotExist:
                                user_email = "el.nico.taz36@gmail.com"
                            
                            # Obtener el nombre de la tienda
                            try:
                                store = Stores.objects.get(id_store=id_store)
                                store_name = store.name
                            except Stores.DoesNotExist:
                                store_name = "Tienda"
                            
                            # Función para enviar email en segundo plano
                            def enviar_alerta_async():
                                time.sleep(0.6)  # Respetar límite de 2 req/seg
                                enviar_alerta_stock_bajo(nombre_producto, int(nuevo_stock), store_name, user_email)
                            
                            # Iniciar thread en segundo plano
                            thread = Thread(target=enviar_alerta_async)
                            thread.daemon = True
                            thread.start()
            
            # Registrar movimiento de creación de venta
            _registrar_movimiento(
                user_id=user_id,
                type_movement='venta',
                type_action='creacion',
                id_sale=id_sale_generado
            )
            
            messages.success(request, f'Venta registrada exitosamente. ID: {id_sale_generado}')
            return redirect('ventas')
            
        except json.JSONDecodeError:
            messages.error(request, 'Error al procesar los productos')
            return redirect('crear_venta')
        except Exception as e:
            messages.error(request, f'Error al crear la venta: {str(e)}')
            return redirect('crear_venta')

def detalle_venta_view(request, sale_id):
    # Verificar autenticación
    user_id = request.session.get('user_id') or _get_user_from_cookie(request)
    if not user_id:
        return redirect('login')
    
    # Obtener el usuario y su tienda
    try:
        user = Users.objects.select_related('id_store').get(id_user=user_id)
        user_store = user.id_store
        if not user_store:
            messages.error(request, 'No tienes una tienda asignada')
            return redirect('ventas')
    except Users.DoesNotExist:
        return redirect('login')
    
    try:
        # Verificar que la venta pertenece a la tienda a través de sales_movement
        venta_ids_permitidos = SalesMovement.objects.filter(
            id_user__id_store=user_store,
            id_sale=sale_id
        ).values_list('id_sale', flat=True)
        
        if not venta_ids_permitidos.exists():
            messages.error(request, 'Venta no encontrada o no tienes permisos para verla')
            return redirect('ventas')
        
        # Obtener la venta
        venta = Sales.objects.get(id_sale=sale_id)
        
        # Por ahora, sin productos relacionados ya que no está la tabla sales_bag
        context = {
            'venta': venta,
            'productos_venta': [],
        }
        
        return render(request, 'core/detalle_venta.html', context)
        
    except Sales.DoesNotExist:
        messages.error(request, 'Venta no encontrada o no tienes permisos para verla')
        return redirect('ventas')

def cancelar_venta_view(request, sale_id):
    """Cancela una venta"""
    # Verificar autenticación
    user_id = request.session.get('user_id') or _get_user_from_cookie(request)
    if not user_id:
        return redirect('login')
    
    # Obtener el usuario y su tienda
    try:
        user = Users.objects.select_related('id_store').get(id_user=user_id)
        user_store = user.id_store
        if not user_store:
            messages.error(request, 'No tienes una tienda asignada')
            return redirect('ventas')
    except Users.DoesNotExist:
        return redirect('login')
    
    try:
        # Verificar que la venta pertenece a la tienda a través de sales_movement
        venta_permitida = SalesMovement.objects.filter(
            id_user__id_store=user_store,
            id_sale=sale_id
        ).exists()
        
        if not venta_permitida:
            messages.error(request, 'Venta no encontrada o no tienes permisos para cancelarla')
            return redirect('ventas')
        
        with connection.cursor() as cursor:
            # Marcar venta como cancelada
            cursor.execute("""
                UPDATE sales 
                SET state = FALSE 
                WHERE id_sale = %s
            """, [sale_id])
        
        # Registrar movimiento de eliminación (cancelación)
        _registrar_movimiento(
            user_id=user_id,
            type_movement='venta',
            type_action='eliminacion',
            id_sale=sale_id
        )
        
        messages.success(request, 'Venta cancelada exitosamente')
    except Exception as e:
        messages.error(request, f'Error al cancelar la venta: {str(e)}')
    
    return redirect('ventas')

def editar_venta_view(request, sale_id):
    """Edita una venta (método de pago y estado)"""
    # Verificar autenticación
    user_id = request.session.get('user_id') or _get_user_from_cookie(request)
    if not user_id:
        return redirect('login')
    
    # Obtener el usuario y su tienda
    try:
        user = Users.objects.select_related('id_store').get(id_user=user_id)
        user_store = user.id_store
        if not user_store:
            messages.error(request, 'No tienes una tienda asignada')
            return redirect('ventas')
    except Users.DoesNotExist:
        return redirect('login')
    
    if request.method == 'POST':
        try:
            pay_method = request.POST.get('pay_method', '').strip()
            state = request.POST.get('state', '').strip()
            
            # Validaciones
            if not pay_method:
                messages.error(request, 'El método de pago es obligatorio')
                return redirect('editar_venta', sale_id=sale_id)
            
            if state not in ['true', 'false']:
                messages.error(request, 'Estado inválido')
                return redirect('editar_venta', sale_id=sale_id)
            
            # Convertir estado a booleano
            state_bool = state == 'true'
            
            # Verificar que la venta pertenece a la tienda a través de sales_movement
            venta_permitida = SalesMovement.objects.filter(
                id_user__id_store=user_store,
                id_sale=sale_id
            ).exists()
            
            if not venta_permitida:
                messages.error(request, 'Venta no encontrada o no tienes permisos para editarla')
                return redirect('ventas')
            
            with connection.cursor() as cursor:
                # Obtener el estado actual de la venta
                cursor.execute("""
                    SELECT state FROM sales WHERE id_sale = %s
                """, [sale_id])
                resultado = cursor.fetchone()
                
                if not resultado:
                    messages.error(request, 'Venta no encontrada o no tienes permisos para editarla')
                    return redirect('ventas')
                
                estado_actual = resultado[0]
                
                # Regla: Si está cancelada (False), NO puede volver a completada (True)
                if not estado_actual and state_bool:
                    messages.error(request, 'No se puede cambiar una venta cancelada a completada')
                    return redirect('editar_venta', sale_id=sale_id)
                
                # Determinar el tipo de acción para el registro
                tipo_accion = None
                
                # Si se está cancelando la venta (cambio de True a False), restaurar stock
                if estado_actual and not state_bool:
                    # Obtener los productos de la venta desde sales_bag
                    cursor.execute("""
                        SELECT id_product, quantitity 
                        FROM sales_bag 
                        WHERE id_sale = %s
                    """, [sale_id])
                    productos_venta = cursor.fetchall()
                    
                    # Restaurar el stock de cada producto
                    for producto_id, cantidad in productos_venta:
                        cursor.execute("""
                            UPDATE products 
                            SET stock = stock + %s 
                            WHERE id_product = %s
                        """, [cantidad, producto_id])
                    
                    tipo_accion = 'eliminacion'
                    messages.success(request, 'Venta cancelada y stock restaurado exitosamente')
                else:
                    tipo_accion = 'modificacion'
                    messages.success(request, 'Venta actualizada exitosamente')
                
                # Actualizar la venta
                cursor.execute("""
                    UPDATE sales 
                    SET pay_method = %s, state = %s 
                    WHERE id_sale = %s
                """, [pay_method, state_bool, sale_id])
            
            # Registrar movimiento según el tipo de acción
            _registrar_movimiento(
                user_id=user_id,
                type_movement='venta',
                type_action=tipo_accion,
                id_sale=sale_id
            )
            
            return redirect('ventas')
            
        except Exception as e:
            messages.error(request, f'Error al editar la venta: {str(e)}')
            return redirect('editar_venta', sale_id=sale_id)
    
    # GET: Mostrar formulario de edición
    try:
        # Verificar que la venta pertenece a la tienda a través de sales_movement
        venta_permitida = SalesMovement.objects.filter(
            id_user__id_store=user_store,
            id_sale=sale_id
        ).exists()
        
        if not venta_permitida:
            messages.error(request, 'Venta no encontrada o no tienes permisos para editarla')
            return redirect('ventas')
        
        with connection.cursor() as cursor:
            # Obtener datos de la venta
            cursor.execute("""
                SELECT id_sale, date_sale, items, total, pay_method, state
                FROM sales
                WHERE id_sale = %s
            """, [sale_id])
            venta_data = cursor.fetchone()
            
            if not venta_data:
                messages.error(request, 'Venta no encontrada')
                return redirect('ventas')
            
            venta = {
                'id_sale': venta_data[0],
                'date_sale': venta_data[1],
                'items': venta_data[2],
                'total': venta_data[3],
                'pay_method': venta_data[4],
                'state': venta_data[5]
            }
            
            # Obtener productos de la venta
            cursor.execute("""
                SELECT p.name, sb.quantitity
                FROM sales_bag sb
                INNER JOIN products p ON sb.id_product = p.id_product
                WHERE sb.id_sale = %s
            """, [sale_id])
            
            productos_venta = []
            for nombre, cantidad in cursor.fetchall():
                productos_venta.append({
                    'nombre': nombre,
                    'cantidad': cantidad
                })
            
            context = {
                'venta': venta,
                'productos_venta': productos_venta
            }
            
            return render(request, 'core/editar_venta.html', context)
            
    except Exception as e:
        messages.error(request, f'Error al cargar la venta: {str(e)}')
        return redirect('ventas')

def usuarios_view(request):
    # Verificar autenticación
    user_id = request.session.get('user_id') or _get_user_from_cookie(request)
    if not user_id:
        return redirect('login')
    
    # Verificar si es admin
    if not request.session.get('is_admin', False):
        messages.error(request, 'No tienes permisos para acceder a esta página')
        return redirect('dashboard')
    
    # Obtener el id_store del usuario autenticado
    try:
        usuario_actual = Users.objects.get(id_user=user_id)
        id_store_actual = usuario_actual.id_store_id
    except Users.DoesNotExist:
        messages.error(request, 'No se pudo obtener la información de tu tienda')
        return redirect('dashboard')
    
    # Obtener solo usuarios de la misma tienda
    usuarios = Users.objects.select_related('usersinfo').filter(id_store_id=id_store_actual)
    
    # Aplicar filtro de búsqueda general
    search_query = request.GET.get('search', '')
    
    if search_query:
        # Buscar en username o en nombre
        usuarios = usuarios.filter(
            Q(username__icontains=search_query) | 
            Q(usersinfo__name__icontains=search_query)
        )
    
    # Calcular estadísticas (solo de la tienda actual)
    total_usuarios_general = Users.objects.filter(id_store_id=id_store_actual).count()
    usuarios_activos = Users.objects.filter(id_store_id=id_store_actual, state_user=True).count()
    usuarios_inactivos = Users.objects.filter(id_store_id=id_store_actual, state_user=False).count()
    administradores = Users.objects.filter(id_store_id=id_store_actual, type_user=True).count()
    
    context = {
        'usuarios': usuarios,
        'total_usuarios': total_usuarios_general,
        'usuarios_activos': usuarios_activos,
        'usuarios_inactivos': usuarios_inactivos,
        'administradores': administradores,
        'search_query': search_query,
        'resultados_filtrados': usuarios.count(),
    }
    
    return render(request, 'core/usuarios.html', context)

def crear_usuario_view(request):
    # Verificar autenticación
    user_id = request.session.get('user_id') or _get_user_from_cookie(request)
    if not user_id:
        return redirect('login')
    # Verificar si es admin
    if not request.session.get('is_admin', False):
        messages.error(request, 'No tienes permisos para acceder a esta página')
        return redirect('dashboard')
    
    # Obtener el id_store del usuario autenticado
    try:
        usuario_actual = Users.objects.select_related('usersinfo').get(id_user=user_id)
        id_store_actual = usuario_actual.id_store_id  # id_store del usuario que está creando
    except Users.DoesNotExist:
        messages.error(request, 'No se pudo obtener la información de tu tienda')
        return redirect('dashboard')
    
    if request.method == 'GET':
        return render(request, 'core/crear_usuario.html')
    
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            username = request.POST.get('username')
            password = request.POST.get('password')
            type_user = request.POST.get('type_user') == '1'  # Convertir a boolean
            state_user = request.POST.get('state_user') == '1'  # Convertir a boolean
            
            name = request.POST.get('name')
            email = request.POST.get('email')
            rut = request.POST.get('rut')
            born_date = request.POST.get('born_date')
            
            # Validar que el username no exista
            if Users.objects.filter(username=username).exists():
                messages.error(request, f'El usuario "{username}" ya existe')
                return render(request, 'core/crear_usuario.html')
            
            # Hashear la contraseña
            hashed_password = hash_password(password)
            
            # Usar SQL directo para crear usuario con el id_store del usuario actual
            with connection.cursor() as cursor:
                # Insertar en tabla users (incluyendo id_store del usuario autenticado)
                cursor.execute("""
                    INSERT INTO users (username, password, type_user, state_user, id_store) 
                    VALUES (%s, %s, %s, %s, %s) 
                    RETURNING id_user
                """, [username, hashed_password, type_user, state_user, id_store_actual])
                
                # Obtener el id_user generado
                id_user_generado = cursor.fetchone()[0]
                
                # Insertar en tabla users_info
                cursor.execute("""
                    INSERT INTO users_info (id_user, name, email, rut, born_date) 
                    VALUES (%s, %s, %s, %s, %s)
                """, [id_user_generado, name, email, rut, born_date])
            
            messages.success(request, f'Usuario "{username}" creado exitosamente en tu tienda')
            return redirect('usuarios')
            
        except Exception as e:
            messages.error(request, f'Error al crear usuario: {str(e)}')
            return render(request, 'core/crear_usuario.html')
    
def agregar_producto_view(request):
    # Verificar autenticación
    user_id = request.session.get('user_id') or _get_user_from_cookie(request)
    if not user_id:
        return redirect('login')
    
    if request.method == 'POST':
        # Obtener datos del formulario
        name = request.POST.get('name', '').strip()
        stock = request.POST.get('stock', '').strip()
        price_sale = request.POST.get('price_sale', '').strip()
        price_buy = request.POST.get('price_buy', '').strip()
        category = request.POST.get('category', '').strip()
        description = request.POST.get('description', '').strip()
        image_file = request.FILES.get('image')
        
        # Validar campos requeridos
        if not name:
            messages.error(request, 'El nombre del producto es obligatorio')
            return redirect('agregar_producto')
        
        if not stock:
            messages.error(request, 'El stock es obligatorio')
            return redirect('agregar_producto')
        
        if not price_sale:
            messages.error(request, 'El precio de venta es obligatorio')
            return redirect('agregar_producto')
        
        if not price_buy:
            messages.error(request, 'El precio de compra es obligatorio')
            return redirect('agregar_producto')
        
        if not category:
            messages.error(request, 'La categoría es obligatoria')
            return redirect('agregar_producto')
        
        if not description:
            messages.error(request, 'La descripción es obligatoria')
            return redirect('agregar_producto')
        
        if not image_file:
            messages.error(request, 'La imagen del producto es obligatoria')
            return redirect('agregar_producto')
        
        try:
            # Obtener el usuario actual
            user = Users.objects.get(id_user=user_id)
            
            # Obtener el id_store del usuario (puede ser None)
            user_store = user.id_store
            
            if not user_store:
                messages.error(request, 'No tienes una tienda asignada. Contacta al administrador.')
                return redirect('agregar_producto')
            
            # Obtener la categoría seleccionada y verificar que pertenezca a la misma tienda
            try:
                categoria_obj = Category.objects.get(id_category=category, id_store=user_store)
                nombre_categoria = categoria_obj.name_category
            except Category.DoesNotExist:
                messages.error(request, 'Categoría no válida o no pertenece a tu tienda')
                return redirect('agregar_producto')
            
            # Leer la imagen y convertirla a bytes
            image_bytes = image_file.read()
            
            # Crear el producto usando SQL directo (PostgreSQL genera el UUID automáticamente)
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO products (name, stock, price_sale, price_buy, category, description, image, id_store, status_product) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) 
                    RETURNING id_product
                """, [name, int(float(stock)), int(float(price_sale)), int(float(price_buy)), nombre_categoria, description, image_bytes, user_store.id_store, True])
                
                # Obtener el id_product generado
                id_product_generado = cursor.fetchone()[0]
            
            # Registrar movimiento de creación de producto
            _registrar_movimiento(
                user_id=user_id,
                type_movement='producto',
                type_action='creacion',
                id_product=id_product_generado
            )
            
            messages.success(request, f'Producto "{name}" agregado exitosamente')
            return redirect('productos')
            
        except Users.DoesNotExist:
            messages.error(request, 'Usuario no encontrado')
            return redirect('agregar_producto')
        except ValueError as e:
            messages.error(request, 'Error en los valores numéricos. Verifica el stock y los precios.')
            return redirect('agregar_producto')
        except Exception as e:
            messages.error(request, f'Error al agregar el producto: {str(e)}')
            return redirect('agregar_producto')
    
    # GET request - mostrar formulario
    # Obtener el usuario actual para obtener su tienda
    try:
        user = Users.objects.get(id_user=user_id)
        user_store = user.id_store
        
        # Obtener solo las categorías de la tienda del usuario
        if user_store:
            categorias = Category.objects.filter(id_store=user_store).order_by('name_category')
        else:
            categorias = Category.objects.none()
            messages.warning(request, 'No tienes una tienda asignada. Contacta al administrador.')
    except Users.DoesNotExist:
        categorias = Category.objects.none()
        messages.error(request, 'Usuario no encontrado')
    
    context = {
        'categorias': categorias
    }
    
    return render(request, 'core/agregar_producto.html', context)

def eliminar_producto_view(request, producto_id):
    # Verificar autenticación
    user_id = request.session.get('user_id') or _get_user_from_cookie(request)
    if not user_id:
        return redirect('login')
    
    # Obtener el usuario y su tienda
    try:
        user = Users.objects.select_related('id_store').get(id_user=user_id)
        user_store = user.id_store
        if not user_store:
            messages.error(request, 'No tienes una tienda asignada')
            return redirect('productos')
    except Users.DoesNotExist:
        return redirect('login')
    
    # Solo permitir POST
    if request.method == 'POST':
        try:
            # Buscar el producto Y verificar que pertenece a la tienda del usuario
            producto = Products.objects.get(id_product=producto_id, id_store=user_store)
            
            # Guardar el nombre antes de cambiar el estado
            nombre_producto = producto.name
            
            # Cambiar el estado a False (soft delete)
            producto.status_product = False
            producto.save(user_id=user_id)
            
            # Registrar movimiento de eliminación de producto
            _registrar_movimiento(
                user_id=user_id,
                type_movement='producto',
                type_action='eliminacion',
                id_product=producto_id
            )
            
            messages.success(request, f'Producto "{nombre_producto}" eliminado exitosamente')
        except Products.DoesNotExist:
            messages.error(request, 'Producto no encontrado o no tienes permisos para eliminarlo')
        except Exception as e:
            messages.error(request, f'Error al eliminar el producto: {str(e)}')
    
    return redirect('productos')
    

def editar_producto_view(request, producto_id):
    """Edita un producto existente"""
    # Verificar autenticación
    user_id = request.session.get('user_id') or _get_user_from_cookie(request)
    if not user_id:
        return redirect('login')
    
    # Obtener el usuario y su tienda
    try:
        user = Users.objects.select_related('id_store').get(id_user=user_id)
        user_store = user.id_store
        if not user_store:
            messages.error(request, 'No tienes una tienda asignada')
            return redirect('productos')
    except Users.DoesNotExist:
        return redirect('login')
    
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            name = request.POST.get('name', '').strip()
            stock = request.POST.get('stock', '').strip()
            price_sale = request.POST.get('price_sale', '').strip()
            price_buy = request.POST.get('price_buy', '').strip()
            category = request.POST.get('category', '').strip()
            description = request.POST.get('description', '').strip()
            image_file = request.FILES.get('image')  # Obtener archivo de imagen si existe
            
            # Validar campos requeridos
            if not all([name, stock, price_sale, price_buy, category, description]):
                messages.error(request, 'Todos los campos son obligatorios')
                return redirect('editar_producto', producto_id=producto_id)
            
            # Buscar el producto Y verificar que pertenece a la tienda del usuario
            producto = Products.objects.get(id_product=producto_id, id_store=user_store)
            
            # Obtener el nombre de la categoría desde el ID Y verificar que pertenece a la tienda
            try:
                categoria_obj = Category.objects.get(id_category=category, id_store=user_store)
                nombre_categoria = categoria_obj.name_category
            except Category.DoesNotExist:
                messages.error(request, 'Categoría no válida o no pertenece a tu tienda')
                return redirect('editar_producto', producto_id=producto_id)
            
            # Actualizar los datos
            producto.name = name
            producto.stock = int(float(stock))
            producto.price_sale = int(float(price_sale))
            producto.price_buy = int(float(price_buy))
            producto.category = nombre_categoria
            producto.description = description
            
            # Si se subió una nueva imagen, actualizarla
            if image_file:
                producto.image = image_file.read()
            
            producto.save(user_id=user_id)
            
            # Registrar movimiento de modificación
            _registrar_movimiento(
                user_id=user_id,
                type_movement='producto',
                type_action='modificacion',
                id_product=producto_id
            )
            
            messages.success(request, f'Producto "{name}" actualizado exitosamente')
            return redirect('productos')
            
        except Products.DoesNotExist:
            messages.error(request, 'Producto no encontrado o no tienes permisos para editarlo')
            return redirect('productos')
        except ValueError:
            messages.error(request, 'Error en los valores numéricos. Verifica el stock y los precios.')
            return redirect('editar_producto', producto_id=producto_id)
        except Exception as e:
            messages.error(request, f'Error al actualizar el producto: {str(e)}')
            return redirect('editar_producto', producto_id=producto_id)
    
    # GET: Mostrar formulario con datos actuales
    try:
        # Buscar el producto Y verificar que pertenece a la tienda del usuario
        producto = Products.objects.get(id_product=producto_id, id_store=user_store)
        
        # Obtener solo las categorías de la tienda del usuario
        if user_store:
            categorias = Category.objects.filter(id_store=user_store).order_by('name_category')
        else:
            categorias = Category.objects.none()
        
        # Buscar la categoría actual del producto por nombre para obtener su ID
        categoria_actual_id = None
        if producto.category:
            try:
                categoria_actual = Category.objects.get(name_category=producto.category, id_store=user_store)
                categoria_actual_id = str(categoria_actual.id_category)
            except Category.DoesNotExist:
                pass
        
        # Convertir imagen a base64 si existe
        imagen_base64 = None
        if producto.image:
            try:
                import base64
                imagen_base64 = base64.b64encode(bytes(producto.image)).decode('utf-8')
            except Exception:
                pass
        
        context = {
            'producto': producto,
            'categorias': categorias,
            'categoria_actual_id': categoria_actual_id,
            'imagen_base64': imagen_base64,
        }
        
        return render(request, 'core/editar_producto.html', context)
        
    except Products.DoesNotExist:
        messages.error(request, 'Producto no encontrado')
        return redirect('productos')
    except Users.DoesNotExist:
        messages.error(request, 'Usuario no encontrado')
        return redirect('productos')


def desactivar_usuario_view(request, user_id):
    """Desactiva un usuario cambiando su state_user a False"""
    # Verificar autenticación
    logged_user_id = request.session.get('user_id') or _get_user_from_cookie(request)
    
    if not logged_user_id:
        return redirect('login')
    
    try:
        # Actualizar el estado del usuario a False (desactivado)
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE users 
                SET state_user = FALSE 
                WHERE id_user = %s
            """, [user_id])
        
        messages.success(request, 'Usuario desactivado exitosamente')
    except Exception as e:
        messages.error(request, f'Error al desactivar usuario: {str(e)}')
    
    return redirect('usuarios')

def editar_usuario_view(request, user_id):
    """Edita un usuario existente"""
    # Verificar autenticación
    logged_user_id = request.session.get('user_id') or _get_user_from_cookie(request)
    
    if not logged_user_id:
        return redirect('login')
    
    if request.method == 'GET':
        try:
            # Obtener datos del usuario
            usuario = Users.objects.select_related('usersinfo').get(id_user=user_id)
            
            context = {
                'usuario': usuario,
            }
            return render(request, 'core/editar_usuario.html', context)
        
        except Users.DoesNotExist:
            messages.error(request, 'Usuario no encontrado')
            return redirect('usuarios')
    
    elif request.method == 'POST':
        try:
            # Obtener datos del formulario
            username = request.POST.get('username')
            password = request.POST.get('password')
            type_user = request.POST.get('type_user') == '1'
            state_user = request.POST.get('state_user') == '1'
            
            name = request.POST.get('name')
            email = request.POST.get('email')
            rut = request.POST.get('rut')
            born_date = request.POST.get('born_date')
            
            # Validaciones básicas
            if not all([username, name, email, rut, born_date]):
                messages.error(request, 'Todos los campos son requeridos')
                return redirect('editar_usuario', user_id=user_id)
            
            # Verificar si el username ya existe (excepto el actual)
            if Users.objects.exclude(id_user=user_id).filter(username=username).exists():
                messages.error(request, f'El usuario "{username}" ya existe')
                return redirect('editar_usuario', user_id=user_id)
            
            # Actualizar usuario con SQL directo
            with connection.cursor() as cursor:
                # Si se proporcionó contraseña, actualizarla también (hasheada)
                if password:
                    hashed_password = hash_password(password)
                    cursor.execute("""
                        UPDATE users 
                        SET username = %s, password = %s, type_user = %s, state_user = %s 
                        WHERE id_user = %s
                    """, [username, hashed_password, type_user, state_user, user_id])
                else:
                    cursor.execute("""
                        UPDATE users 
                        SET username = %s, type_user = %s, state_user = %s 
                        WHERE id_user = %s
                    """, [username, type_user, state_user, user_id])
                
                # Actualizar información personal
                cursor.execute("""
                    UPDATE users_info 
                    SET name = %s, email = %s, rut = %s, born_date = %s 
                    WHERE id_user = %s
                """, [name, email, rut, born_date, user_id])
            
            messages.success(request, f'Usuario "{username}" actualizado exitosamente')
            return redirect('usuarios')
            
        except Exception as e:
            messages.error(request, f'Error al actualizar usuario: {str(e)}')
            return redirect('editar_usuario', user_id=user_id)

def historial_movimientos_view(request):
    """Muestra el historial de movimientos de productos y ventas"""
    # Verificar autenticación
    user_id = request.session.get('user_id') or _get_user_from_cookie(request)
    if not user_id:
        return redirect('login')
    
    # Obtener el usuario y su tienda
    try:
        user = Users.objects.select_related('id_store').get(id_user=user_id)
        user_store = user.id_store
        if not user_store:
            return HttpResponse("Usuario sin tienda asignada", status=400)
    except Users.DoesNotExist:
        return redirect('login')
    
    try:
        # Obtener filtros
        type_movement = request.GET.get('type_movement', '')
        type_action = request.GET.get('type_action', '')
        fecha_inicio = request.GET.get('fecha_inicio', '')
        fecha_fin = request.GET.get('fecha_fin', '')
        
        with connection.cursor() as cursor:
            # Construir query con joins para obtener información completa
            # Filtrar por la tienda del usuario a través de la tabla users
            query = """
                SELECT 
                    sm.id_movement,
                    sm.type_movement,
                    sm.type_action,
                    sm.date_movement,
                    sm.id_sale,
                    sm.id_product,
                    sm.id_user,
                    u.username,
                    ui.name as user_name,
                    p.name as product_name,
                    s.total as sale_total
                FROM sales_movement sm
                LEFT JOIN users u ON sm.id_user = u.id_user
                LEFT JOIN users_info ui ON u.id_user = ui.id_user
                LEFT JOIN products p ON sm.id_product = p.id_product
                LEFT JOIN sales s ON sm.id_sale = s.id_sale
                WHERE u.id_store = %s
            """
            params = [str(user_store.id_store)]
            
            # Aplicar filtros
            if type_movement:
                query += " AND sm.type_movement = %s"
                params.append(type_movement)
            
            if type_action:
                query += " AND sm.type_action = %s"
                params.append(type_action)
            
            if fecha_inicio:
                query += " AND sm.date_movement >= %s"
                params.append(fecha_inicio)
            
            if fecha_fin:
                query += " AND sm.date_movement <= %s"
                params.append(fecha_fin)
            
            query += " ORDER BY sm.date_movement DESC, sm.id_movement DESC LIMIT 100"
            
            cursor.execute(query, params)
            columnas = [col[0] for col in cursor.description]
            resultados = cursor.fetchall()
            
            # Convertir a lista de diccionarios
            movimientos = []
            for fila in resultados:
                movimiento = dict(zip(columnas, fila))
                movimientos.append(movimiento)
        
        context = {
            'movimientos': movimientos,
            'type_movement': type_movement,
            'type_action': type_action,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
        }
        
        return render(request, 'core/historial_movimientos.html', context)
        
    except Exception as e:
        messages.error(request, f'Error al cargar el historial: {str(e)}')
        return redirect('dashboard')


def producto_imagen_view(request, producto_id):
    """Sirve la imagen de un producto desde la base de datos"""
    try:
        producto = Products.objects.get(id_product=producto_id)
        
        # Si el producto tiene imagen, devolverla
        if producto.image:
            return HttpResponse(producto.image, content_type='image/jpeg')
        else:
            # Si no tiene imagen, devolver una imagen por defecto o un 404
            return HttpResponse(status=404)
            
    except Products.DoesNotExist:
        return HttpResponse(status=404)


def crear_categoria_view(request):
    """Crea una nueva categoría mediante AJAX"""
    if request.method == 'POST':
        # Verificar autenticación
        user_id = request.session.get('user_id') or _get_user_from_cookie(request)
        if not user_id:
            return JsonResponse({'success': False, 'error': 'No autenticado'})
        
        try:
            nombre = request.POST.get('nombre', '').strip()
            
            if not nombre:
                return JsonResponse({'success': False, 'error': 'El nombre es obligatorio'})
            
            # Obtener el usuario y su tienda
            user = Users.objects.get(id_user=user_id)
            user_store = user.id_store
            
            if not user_store:
                return JsonResponse({'success': False, 'error': 'No tienes una tienda asignada'})
            
            # Verificar si la categoría ya existe en la tienda
            if Category.objects.filter(name_category=nombre, id_store=user_store).exists():
                return JsonResponse({'success': False, 'error': 'Ya existe una categoría con ese nombre'})
            
            # Crear la nueva categoría
            nueva_categoria = Category.objects.create(
                name_category=nombre,
                id_store=user_store
            )
            
            return JsonResponse({
                'success': True,
                'id': str(nueva_categoria.id_category),
                'nombre': nueva_categoria.name_category
            })
            
        except Users.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Usuario no encontrado'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})


def superusuario_view(request):
    """Vista exclusiva para superusuario - Gestión de tiendas y administradores"""
    # Verificar autenticación de superadmin
    if not request.session.get('is_superadmin'):
        messages.error(request, 'Acceso denegado. Esta área es solo para superadministradores.')
        return redirect('login')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # Crear nueva tienda
        if action == 'crear_tienda':
            try:
                store_name = request.POST.get('store_name', '').strip()
                store_direction = request.POST.get('store_direction', '').strip()
                store_phone = request.POST.get('store_phone', '').strip()
                store_admin = request.POST.get('store_admin', '').strip()
                
                if not all([store_name, store_direction, store_phone, store_admin]):
                    messages.error(request, 'Todos los campos son obligatorios')
                    return redirect('superusuario')
                
                # Crear la tienda
                nueva_tienda = Stores.objects.create(
                    name=store_name,
                    direction=store_direction,
                    phone=store_phone,
                    administrator_name=store_admin
                )
                
                messages.success(request, f'Tienda "{store_name}" creada exitosamente')
                return redirect('superusuario')
                
            except Exception as e:
                messages.error(request, f'Error al crear la tienda: {str(e)}')
                return redirect('superusuario')
        
        # Crear usuario administrador
        elif action == 'crear_admin':
            try:
                store_id = request.POST.get('store_id', '').strip()
                name = request.POST.get('name', '').strip()
                email = request.POST.get('email', '').strip()
                rut = request.POST.get('rut', '').strip()
                born_date = request.POST.get('born_date', '').strip()
                username = request.POST.get('username', '').strip()
                password = request.POST.get('password', '').strip()
                
                if not all([store_id, name, email, rut, born_date, username, password]):
                    messages.error(request, 'Todos los campos son obligatorios')
                    return redirect('superusuario')
                
                # Verificar si el username ya existe
                if Users.objects.filter(username=username).exists():
                    messages.error(request, 'El nombre de usuario ya existe')
                    return redirect('superusuario')
                
                # Obtener la tienda
                tienda = Stores.objects.get(id_store=store_id)
                
                # Hashear la contraseña
                hashed_password = hash_password(password)
                
                # Crear el usuario
                nuevo_usuario = Users.objects.create(
                    username=username,
                    password=hashed_password,
                    type_user=True,  # True = Administrador
                    state_user=True,  # Usuario activo
                    id_store=tienda
                )
                
                # Crear la información adicional del usuario
                UsersInfo.objects.create(
                    id_user=nuevo_usuario,
                    name=name,
                    email=email,
                    rut=rut,
                    born_date=born_date
                )
                
                messages.success(request, f'Usuario administrador "{username}" creado exitosamente para la tienda "{tienda.name}"')
                return redirect('superusuario')
                
            except Stores.DoesNotExist:
                messages.error(request, 'Tienda no encontrada')
                return redirect('superusuario')
            except Exception as e:
                messages.error(request, f'Error al crear el usuario: {str(e)}')
                return redirect('superusuario')
    
    # GET: Mostrar formulario
    tiendas = Stores.objects.all().order_by('name')
    
    context = {
        'tiendas': tiendas
    }
    
    return render(request, 'core/superusuario.html', context)


# ========================================
# API ENDPOINTS PARA GRÁFICOS BI
# ========================================

from django.http import JsonResponse
from django.db.models import Sum, Count
from datetime import datetime, timedelta

def api_ventas_por_dia(request):
    """API: Ventas por día (últimos 30 días)"""
    user_id = request.session.get('user_id') or _get_user_from_cookie(request)
    if not user_id:
        return JsonResponse({'error': 'No autenticado'}, status=401)
    
    try:
        user = Users.objects.select_related('id_store').get(id_user=user_id)
        user_store = user.id_store
        if not user_store:
            return JsonResponse({'error': 'Sin tienda asignada'}, status=400)
    except Users.DoesNotExist:
        return JsonResponse({'error': 'Usuario no encontrado'}, status=404)
    
    # Obtener ventas de la tienda
    ventas_ids = SalesMovement.objects.filter(
        id_user__id_store=user_store,
        type_movement='venta'
    ).values_list('id_sale', flat=True).distinct()
    
    # Últimos 30 días
    hoy = datetime.now().date()
    hace_30_dias = hoy - timedelta(days=30)
    
    ventas_por_dia = Sales.objects.filter(
        id_sale__in=ventas_ids,
        state=True,
        date_sale__gte=hace_30_dias
    ).values('date_sale').annotate(
        total_ventas=Sum('total'),
        cantidad_ventas=Count('id_sale')
    ).order_by('date_sale')
    
    datos = {
        'labels': [v['date_sale'].strftime('%d/%m') for v in ventas_por_dia],
        'ventas': [float(v['total_ventas']) for v in ventas_por_dia],
        'cantidad': [v['cantidad_ventas'] for v in ventas_por_dia]
    }
    
    return JsonResponse(datos)


def api_ventas_por_mes(request):
    """API: Ventas por mes (últimos 12 meses)"""
    user_id = request.session.get('user_id') or _get_user_from_cookie(request)
    if not user_id:
        return JsonResponse({'error': 'No autenticado'}, status=401)
    
    try:
        user = Users.objects.select_related('id_store').get(id_user=user_id)
        user_store = user.id_store
        if not user_store:
            return JsonResponse({'error': 'Sin tienda asignada'}, status=400)
    except Users.DoesNotExist:
        return JsonResponse({'error': 'Usuario no encontrado'}, status=404)
    
    from django.db.models.functions import TruncMonth
    
    # Obtener ventas de la tienda
    ventas_ids = SalesMovement.objects.filter(
        id_user__id_store=user_store,
        type_movement='venta'
    ).values_list('id_sale', flat=True).distinct()
    
    # Últimos 12 meses
    hoy = datetime.now().date()
    hace_12_meses = hoy - timedelta(days=365)
    
    ventas_por_mes = Sales.objects.filter(
        id_sale__in=ventas_ids,
        state=True,
        date_sale__gte=hace_12_meses
    ).annotate(
        mes=TruncMonth('date_sale')
    ).values('mes').annotate(
        total_ventas=Sum('total'),
        cantidad_ventas=Count('id_sale')
    ).order_by('mes')
    
    datos = {
        'labels': [v['mes'].strftime('%B %Y') for v in ventas_por_mes],
        'ventas': [float(v['total_ventas']) for v in ventas_por_mes],
        'cantidad': [v['cantidad_ventas'] for v in ventas_por_mes]
    }
    
    return JsonResponse(datos)


def api_productos_mas_vendidos(request):
    """API: Top 10 productos más vendidos"""
    user_id = request.session.get('user_id') or _get_user_from_cookie(request)
    if not user_id:
        return JsonResponse({'error': 'No autenticado'}, status=401)
    
    try:
        user = Users.objects.select_related('id_store').get(id_user=user_id)
        user_store = user.id_store
        if not user_store:
            return JsonResponse({'error': 'Sin tienda asignada'}, status=400)
    except Users.DoesNotExist:
        return JsonResponse({'error': 'Usuario no encontrado'}, status=404)
    
    # Obtener ventas de la tienda
    ventas_ids = SalesMovement.objects.filter(
        id_user__id_store=user_store,
        type_movement='venta'
    ).values_list('id_sale', flat=True).distinct()
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT p.name, SUM(sb.quantitity) as total_vendido, SUM(s.total) as ingresos
                FROM sales_bag sb
                INNER JOIN products p ON sb.id_product = p.id_product
                INNER JOIN sales s ON sb.id_sale = s.id_sale
                WHERE s.id_sale = ANY(%s) AND s.state = true
                GROUP BY p.id_product, p.name
                ORDER BY total_vendido DESC
                LIMIT 10
            """, [list(ventas_ids)])
            
            productos = []
            for row in cursor.fetchall():
                productos.append({
                    'nombre': row[0],
                    'cantidad': float(row[1]),
                    'ingresos': float(row[2])
                })
            
            datos = {
                'labels': [p['nombre'] for p in productos],
                'cantidades': [p['cantidad'] for p in productos],
                'ingresos': [p['ingresos'] for p in productos]
            }
            
            return JsonResponse(datos)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def api_ventas_por_categoria(request):
    """API: Ventas por categoría de productos"""
    user_id = request.session.get('user_id') or _get_user_from_cookie(request)
    if not user_id:
        return JsonResponse({'error': 'No autenticado'}, status=401)
    
    try:
        user = Users.objects.select_related('id_store').get(id_user=user_id)
        user_store = user.id_store
        if not user_store:
            return JsonResponse({'error': 'Sin tienda asignada'}, status=400)
    except Users.DoesNotExist:
        return JsonResponse({'error': 'Usuario no encontrado'}, status=404)
    
    # Obtener ventas de la tienda
    ventas_ids = SalesMovement.objects.filter(
        id_user__id_store=user_store,
        type_movement='venta'
    ).values_list('id_sale', flat=True).distinct()
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT p.category, SUM(sb.quantitity) as total_vendido, SUM(s.total) as ingresos
                FROM sales_bag sb
                INNER JOIN products p ON sb.id_product = p.id_product
                INNER JOIN sales s ON sb.id_sale = s.id_sale
                WHERE s.id_sale = ANY(%s) AND s.state = true
                GROUP BY p.category
                ORDER BY ingresos DESC
            """, [list(ventas_ids)])
            
            categorias = []
            for row in cursor.fetchall():
                categorias.append({
                    'categoria': row[0],
                    'cantidad': float(row[1]),
                    'ingresos': float(row[2])
                })
            
            datos = {
                'labels': [c['categoria'] for c in categorias],
                'cantidades': [c['cantidad'] for c in categorias],
                'ingresos': [c['ingresos'] for c in categorias]
            }
            
            return JsonResponse(datos)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def api_estado_inventario(request):
    """API: Estado del inventario (stock disponible, bajo, agotado)"""
    user_id = request.session.get('user_id') or _get_user_from_cookie(request)
    if not user_id:
        return JsonResponse({'error': 'No autenticado'}, status=401)
    
    try:
        user = Users.objects.select_related('id_store').get(id_user=user_id)
        user_store = user.id_store
        if not user_store:
            return JsonResponse({'error': 'Sin tienda asignada'}, status=400)
    except Users.DoesNotExist:
        return JsonResponse({'error': 'Usuario no encontrado'}, status=404)
    
    productos_disponibles = Products.objects.filter(
        id_store=user_store,
        status_product=True,
        stock__gte=10
    ).count()
    
    productos_stock_bajo = Products.objects.filter(
        id_store=user_store,
        status_product=True,
        stock__gt=0,
        stock__lt=10
    ).count()
    
    productos_agotados = Products.objects.filter(
        id_store=user_store,
        status_product=True,
        stock=0
    ).count()
    
    datos = {
        'labels': ['Disponible', 'Stock Bajo', 'Agotado'],
        'valores': [productos_disponibles, productos_stock_bajo, productos_agotados],
        'colores': ['#10b981', '#f59e0b', '#ef4444']
    }
    
    return JsonResponse(datos)


def api_comparacion_periodos(request):
    """API: Comparación de ventas entre períodos (este mes vs mes anterior)"""
    user_id = request.session.get('user_id') or _get_user_from_cookie(request)
    if not user_id:
        return JsonResponse({'error': 'No autenticado'}, status=401)
    
    try:
        user = Users.objects.select_related('id_store').get(id_user=user_id)
        user_store = user.id_store
        if not user_store:
            return JsonResponse({'error': 'Sin tienda asignada'}, status=400)
    except Users.DoesNotExist:
        return JsonResponse({'error': 'Usuario no encontrado'}, status=404)
    
    # Obtener ventas de la tienda
    ventas_ids = SalesMovement.objects.filter(
        id_user__id_store=user_store,
        type_movement='venta'
    ).values_list('id_sale', flat=True).distinct()
    
    hoy = datetime.now().date()
    
    # Este mes
    primer_dia_mes_actual = hoy.replace(day=1)
    ventas_mes_actual = Sales.objects.filter(
        id_sale__in=ventas_ids,
        state=True,
        date_sale__gte=primer_dia_mes_actual
    ).aggregate(
        total=Sum('total'),
        cantidad=Count('id_sale')
    )
    
    # Mes anterior
    ultimo_dia_mes_anterior = primer_dia_mes_actual - timedelta(days=1)
    primer_dia_mes_anterior = ultimo_dia_mes_anterior.replace(day=1)
    ventas_mes_anterior = Sales.objects.filter(
        id_sale__in=ventas_ids,
        state=True,
        date_sale__gte=primer_dia_mes_anterior,
        date_sale__lte=ultimo_dia_mes_anterior
    ).aggregate(
        total=Sum('total'),
        cantidad=Count('id_sale')
    )
    
    datos = {
        'labels': ['Mes Anterior', 'Mes Actual'],
        'ventas': [
            float(ventas_mes_anterior['total'] or 0),
            float(ventas_mes_actual['total'] or 0)
        ],
        'cantidad': [
            ventas_mes_anterior['cantidad'] or 0,
            ventas_mes_actual['cantidad'] or 0
        ]
    }
    
    return JsonResponse(datos)

def api_ventas_producto_por_fecha(request):
    """API para obtener ventas de un producto específico por fecha"""
    # Verificar autenticación
    user_id = request.session.get('user_id') or _get_user_from_cookie(request)
    if not user_id:
        return JsonResponse({'error': 'No autenticado'}, status=401)
    
    # Obtener el usuario y su tienda
    try:
        user = Users.objects.select_related('id_store').get(id_user=user_id)
        user_store = user.id_store
        if not user_store:
            return JsonResponse({'error': 'No tienes tienda asignada'}, status=400)
    except Users.DoesNotExist:
        return JsonResponse({'error': 'Usuario no encontrado'}, status=404)
    
    # Obtener el ID del producto
    producto_id = request.GET.get('producto_id')
    if not producto_id:
        return JsonResponse({'error': 'producto_id es requerido'}, status=400)
    
    # Verificar que el producto pertenece a la tienda
    try:
        producto = Products.objects.get(id_product=producto_id, id_store=user_store)
    except Products.DoesNotExist:
        return JsonResponse({'error': 'Producto no encontrado'}, status=404)
    
    # Obtener ventas del producto agrupadas por fecha
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                s.date_sale,
                SUM(sb.quantitity) as cantidad_vendida
            FROM sales_bag sb
            INNER JOIN sales s ON sb.id_sale = s.id_sale
            WHERE sb.id_product = %s AND s.id_store = %s AND s.state = true
            GROUP BY s.date_sale
            ORDER BY s.date_sale
        """, [str(producto_id), str(user_store.id_store)])
        
        rows = cursor.fetchall()
    
    # Formatear datos
    fechas = []
    cantidades = []
    for row in rows:
        fechas.append(row[0].strftime('%Y-%m-%d'))
        cantidades.append(float(row[1]))
    
    datos = {
        'producto_nombre': producto.name,
        'fechas': fechas,
        'cantidades': cantidades
    }
    
    return JsonResponse(datos)
