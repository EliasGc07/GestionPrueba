import resend
from django.conf import settings
import os

# Configurar la API key de Resend
resend.api_key = os.environ.get('RESEND_API_KEY', 're_TA8Vy3p8_NRAoVZGiRFFvnZJ6jz64eZfG')


def enviar_alerta_stock_bajo(producto_name, stock_actual, store_name, to_email):
    """
    Envía un email de alerta cuando el stock de un producto está bajo
    
    Args:
        producto_name (str): Nombre del producto
        stock_actual (int): Cantidad actual en stock
        store_name (str): Nombre de la tienda
        to_email (str): Email del destinatario
    """
    
    # Determinar el nivel de urgencia
    if stock_actual == 0:
        urgencia = "CRÍTICO"
        color = "#ef4444"  # rojo
        emoji = "🔴"
    elif stock_actual < 5:
        urgencia = "ALTO"
        color = "#f59e0b"  # naranja
        emoji = "🟡"
    else:
        urgencia = "MEDIO"
        color = "#3b82f6"  # azul
        emoji = "🟢"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: #f3f4f6;
                margin: 0;
                padding: 20px;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                background-color: white;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                overflow: hidden;
            }}
            .header {{
                background: linear-gradient(135deg, {color} 0%, {color}dd 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 28px;
                font-weight: bold;
            }}
            .urgencia-badge {{
                display: inline-block;
                background-color: rgba(255, 255, 255, 0.3);
                padding: 8px 16px;
                border-radius: 20px;
                margin-top: 10px;
                font-size: 14px;
                font-weight: bold;
            }}
            .content {{
                padding: 30px;
            }}
            .alert-box {{
                background-color: #fef3c7;
                border-left: 4px solid {color};
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 25px;
            }}
            .product-info {{
                background-color: #f9fafb;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 25px;
            }}
            .info-row {{
                display: flex;
                justify-content: space-between;
                padding: 10px 0;
                border-bottom: 1px solid #e5e7eb;
            }}
            .info-row:last-child {{
                border-bottom: none;
            }}
            .label {{
                font-weight: 600;
                color: #374151;
            }}
            .value {{
                color: {color};
                font-weight: bold;
                font-size: 18px;
            }}
            .action-button {{
                display: inline-block;
                background-color: {color};
                color: white;
                padding: 14px 30px;
                text-decoration: none;
                border-radius: 8px;
                font-weight: bold;
                text-align: center;
                margin-top: 20px;
            }}
            .footer {{
                background-color: #f9fafb;
                padding: 20px;
                text-align: center;
                color: #6b7280;
                font-size: 14px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{emoji} Alerta de Stock Bajo</h1>
                <div class="urgencia-badge">NIVEL DE URGENCIA: {urgencia}</div>
            </div>
            
            <div class="content">
                <div class="alert-box">
                    <strong>⚠️ Atención Requerida:</strong> El stock del producto está por debajo del nivel mínimo recomendado.
                </div>
                
                <div class="product-info">
                    <div class="info-row">
                        <span class="label">📦 Producto:</span>
                        <span style="color: #111827; font-weight: 600;">{producto_name}</span>
                    </div>
                    <div class="info-row">
                        <span class="label">🏪 Tienda:</span>
                        <span style="color: #111827;">{store_name}</span>
                    </div>
                    <div class="info-row">
                        <span class="label">📊 Stock Actual:</span>
                        <span class="value">{stock_actual} unidades</span>
                    </div>
                    <div class="info-row">
                        <span class="label">✅ Stock Recomendado:</span>
                        <span style="color: #10b981; font-weight: 600;">10+ unidades</span>
                    </div>
                </div>
                
                <h3 style="color: #111827; margin-top: 25px;">📝 Acciones Recomendadas:</h3>
                <ul style="color: #374151; line-height: 1.8;">
                    <li>Revisar las ventas recientes del producto</li>
                    <li>Contactar al proveedor para realizar un nuevo pedido</li>
                    <li>Considerar promociones alternativas si el stock está agotado</li>
                    <li>Actualizar el sistema con el nuevo pedido realizado</li>
                </ul>
                
                <div style="text-align: center;">
                    <a href="http://127.0.0.1:8000/dashboard/" class="action-button">
                        🔗 Ir al Dashboard
                    </a>
                </div>
            </div>
            
            <div class="footer">
                <p><strong>Sistema de Gestión de Inventario</strong></p>
                <p>Este es un mensaje automático generado por el sistema de alertas.</p>
                <p style="margin-top: 10px; font-size: 12px;">
                    Si no reconoces esta actividad, por favor contacta al administrador del sistema.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        params = {
            "from": "Sistema de Inventario <onboarding@resend.dev>",
            "to": [to_email],
            "subject": f"🚨 Alerta de Stock Bajo: {producto_name} ({stock_actual} unidades restantes)",
            "html": html_content
        }
        
        email = resend.Emails.send(params)
        
        print(f"✅ Email de alerta enviado exitosamente!")
        print(f"   📧 Para: {to_email}")
        print(f"   📦 Producto: {producto_name}")
        print(f"   📊 Stock: {stock_actual}")
        print(f"   🆔 ID Email: {email.get('id', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error al enviar email de alerta: {e}")
        return False


def enviar_alerta_stock_critico_multiple(productos_bajos, store_name, to_email):
    """
    Envía un resumen de múltiples productos con stock bajo
    
    Args:
        productos_bajos (list): Lista de diccionarios con info de productos
        store_name (str): Nombre de la tienda
        to_email (str): Email del destinatario
    """
    
    # Construir tabla de productos
    filas_productos = ""
    for prod in productos_bajos:
        color = "#ef4444" if prod['stock'] == 0 else "#f59e0b" if prod['stock'] < 5 else "#3b82f6"
        filas_productos += f"""
        <tr style="border-bottom: 1px solid #e5e7eb;">
            <td style="padding: 12px; color: #111827;">{prod['name']}</td>
            <td style="padding: 12px; text-align: center; color: {color}; font-weight: bold;">{prod['stock']}</td>
        </tr>
        """
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #f3f4f6; padding: 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; }}
            .header {{ background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); color: white; padding: 30px; text-align: center; border-radius: 12px 12px 0 0; }}
            .content {{ padding: 30px; }}
            table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            th {{ background-color: #f9fafb; padding: 12px; text-align: left; font-weight: bold; color: #374151; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚨 Reporte de Stock Bajo</h1>
                <p>Múltiples productos requieren atención</p>
            </div>
            <div class="content">
                <h3>📍 Tienda: {store_name}</h3>
                <p>Se detectaron <strong>{len(productos_bajos)} productos</strong> con stock bajo o agotado:</p>
                
                <table>
                    <thead>
                        <tr>
                            <th>Producto</th>
                            <th style="text-align: center;">Stock</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filas_productos}
                    </tbody>
                </table>
                
                <p style="color: #6b7280; font-size: 14px; margin-top: 20px;">
                    Por favor, revisa el inventario y realiza los pedidos necesarios.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        params = {
            "from": "Sistema de Inventario <onboarding@resend.dev>",
            "to": [to_email],
            "subject": f"🚨 Reporte de Stock: {len(productos_bajos)} productos con stock bajo",
            "html": html_content
        }
        
        email = resend.Emails.send(params)
        print(f"✅ Reporte de múltiples productos enviado a {to_email}")
        return True
        
    except Exception as e:
        print(f"❌ Error al enviar reporte: {e}")
        return False
