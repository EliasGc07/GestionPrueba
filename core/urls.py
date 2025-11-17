from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Superusuario
    path('superusuario/', views.superusuario_view, name='superusuario'),
    
    # Páginas del sistema
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('productos/', views.productos_view, name='productos'),
    path('ventas/', views.ventas_view, name='ventas'),
    path('usuarios/', views.usuarios_view, name='usuarios'),
    path('usuarios/crear/', views.crear_usuario_view, name='crear_usuario'),
    path('usuarios/editar/<uuid:user_id>/', views.editar_usuario_view, name='editar_usuario'),
    path('usuarios/desactivar/<uuid:user_id>/', views.desactivar_usuario_view, name='desactivar_usuario'),
    
    # Productos urls
    path('productos/agregar/', views.agregar_producto_view, name='agregar_producto'),
    path('productos/editar/<uuid:producto_id>/', views.editar_producto_view, name='editar_producto'),
    path('productos/eliminar/<uuid:producto_id>/', views.eliminar_producto_view, name='eliminar_producto'),
    path('productos/imagen/<uuid:producto_id>/', views.producto_imagen_view, name='producto_imagen'),
    
    # Categorías
    path('categorias/crear/', views.crear_categoria_view, name='crear_categoria'),
    
    # Ventas urls
    path('ventas/crear/', views.crear_venta_view, name='crear_venta'),
    path('ventas/detalle/<uuid:sale_id>/', views.detalle_venta_view, name='detalle_venta'),
    path('ventas/editar/<uuid:sale_id>/', views.editar_venta_view, name='editar_venta'),
    path('ventas/cancelar/<uuid:sale_id>/', views.cancelar_venta_view, name='cancelar_venta'),
    
    # Historial de movimientos
    path('historial/', views.historial_movimientos_view, name='historial_movimientos'),

    # HTMX
    path('click-me/', views.click_me_target, name='click-me'),
    
    # API para gráficos BI
    path('api/ventas-por-dia/', views.api_ventas_por_dia, name='api_ventas_por_dia'),
    path('api/ventas-por-mes/', views.api_ventas_por_mes, name='api_ventas_por_mes'),
    path('api/productos-mas-vendidos/', views.api_productos_mas_vendidos, name='api_productos_mas_vendidos'),
    path('api/ventas-por-categoria/', views.api_ventas_por_categoria, name='api_ventas_por_categoria'),
    path('api/estado-inventario/', views.api_estado_inventario, name='api_estado_inventario'),
    path('api/comparacion-periodos/', views.api_comparacion_periodos, name='api_comparacion_periodos'),
    path('api/ventas-producto-por-fecha/', views.api_ventas_producto_por_fecha, name='api_ventas_producto_por_fecha'),
]