# 🔧 Configuración de Power BI Embedded

## 📋 Estado Actual

He implementado Power BI Embedded con filtros dinámicos en JavaScript. El código está listo pero **necesitas configurar las credenciales de Power BI**.

## ⚠️ PROBLEMA PRINCIPAL

Tu URL actual es de tipo **"Publish to Web"** (público):
```
https://app.powerbi.com/view?r=eyJr...
```

Este tipo de URL **NO soporta**:
- Filtros dinámicos por URL
- Autenticación
- Seguridad a nivel de fila (RLS)

## ✅ SOLUCIONES

### **Opción 1: Usar Power BI Embedded (Recomendado para producción)**

**Requisitos:**
- Suscripción de Azure
- Power BI Pro o Premium
- Configurar Azure AD Application

**Pasos:**

1. **Registrar una aplicación en Azure AD:**
   - Ve a https://portal.azure.com
   - Azure Active Directory → App registrations → New registration
   - Nombre: "Django Gestor Inventario"
   - Redirect URI: `http://127.0.0.1:8000/dashboard/`

2. **Configurar permisos:**
   - API permissions → Add permission → Power BI Service
   - Agregar: `Report.Read.All`, `Dataset.Read.All`

3. **Obtener credenciales:**
   - Copia el **Application (client) ID**
   - Copia el **Directory (tenant) ID**
   - Certificates & secrets → New client secret → Copia el **Value**

4. **Actualizar `settings.py`:**
```python
# Power BI Configuration
POWERBI_CLIENT_ID = "tu-client-id-aqui"
POWERBI_CLIENT_SECRET = "tu-client-secret-aqui"
POWERBI_TENANT_ID = "tu-tenant-id-aqui"
POWERBI_REPORT_ID = "63a87081-9083-404b-86e6-8067672b46af"
POWERBI_GROUP_ID = "tu-workspace-id"  # Desde Power BI Service
```

5. **Instalar librerías:**
```bash
pip install msal requests
```

6. **Crear función para obtener token (en `views.py`):**
```python
import msal
import requests
from django.conf import settings

def get_powerbi_access_token():
    """Obtiene un token de acceso de Azure AD para Power BI"""
    authority = f"https://login.microsoftonline.com/{settings.POWERBI_TENANT_ID}"
    scope = ["https://analysis.windows.net/powerbi/api/.default"]
    
    app = msal.ConfidentialClientApplication(
        settings.POWERBI_CLIENT_ID,
        authority=authority,
        client_credential=settings.POWERBI_CLIENT_SECRET
    )
    
    result = app.acquire_token_for_client(scopes=scope)
    
    if "access_token" in result:
        return result["access_token"]
    else:
        raise Exception(f"Error obteniendo token: {result.get('error_description')}")

def get_embed_params():
    """Obtiene los parámetros de embedding de Power BI"""
    access_token = get_powerbi_access_token()
    
    # Obtener la URL de embedding del reporte
    url = f"https://api.powerbi.com/v1.0/myorg/groups/{settings.POWERBI_GROUP_ID}/reports/{settings.POWERBI_REPORT_ID}"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    response = requests.get(url, headers=headers)
    report = response.json()
    
    return {
        'access_token': access_token,
        'embed_url': report['embedUrl'],
        'report_id': report['id']
    }
```

7. **Actualizar `dashboard_view` para pasar el token:**
```python
def dashboard_view(request):
    # ... tu código existente ...
    
    # Obtener parámetros de Power BI
    try:
        embed_params = get_embed_params()
        context['powerbi_access_token'] = embed_params['access_token']
        context['powerbi_embed_url'] = embed_params['embed_url']
        context['powerbi_report_id'] = embed_params['report_id']
    except Exception as e:
        print(f"Error obteniendo parámetros de Power BI: {e}")
        context['powerbi_access_token'] = ""
        context['powerbi_embed_url'] = ""
        context['powerbi_report_id'] = ""
    
    return render(request, 'core/dashboard.html', context)
```

8. **Actualizar el template (`dashboard.html`):**
```javascript
const EMBED_ACCESS_TOKEN = "{{ powerbi_access_token }}";
const EMBED_URL = "{{ powerbi_embed_url }}";
const REPORT_ID = "{{ powerbi_report_id }}";
```

---

### **Opción 2: Row-Level Security (RLS) en Power BI (Más simple)**

Si no quieres configurar Azure AD, puedes usar RLS:

1. **En Power BI Desktop:**
   - Modeling → Manage Roles → New Role
   - Nombre: "StoreFilter"
   - Agregar filtro DAX:
   ```dax
   [id_store] = USERPRINCIPALNAME()
   ```

2. **Publicar con RLS:**
   - Publish → Seleccionar workspace
   - En Power BI Service → Dataset settings → Row-Level Security
   - Agregar usuarios/emails con su ID de tienda

3. **Usar embed token con RLS:**
   - Necesitas generar un embed token que incluya el RLS
   - El usuario verá solo su tienda automáticamente

---

### **Opción 3: Múltiples reportes (Workaround simple)**

Si no quieres complejidad:

1. Crea un reporte separado para cada tienda
2. En Django, muestra el reporte correcto según `id_store`
3. Usa URLs "Publish to Web" diferentes por tienda

**Ejemplo en `dashboard_view`:**
```python
# Mapeo de tiendas a URLs de reportes
POWERBI_REPORTS = {
    'tienda-1-uuid': 'https://app.powerbi.com/view?r=ABC123...',
    'tienda-2-uuid': 'https://app.powerbi.com/view?r=DEF456...',
}

context['powerbi_url'] = POWERBI_REPORTS.get(
    str(user_store.id_store),
    'https://app.powerbi.com/view?r=default...'
)
```

---

## 🎯 RECOMENDACIÓN

Para tu caso (multi-tienda con seguridad):

1. **Corto plazo:** Usar Opción 3 (múltiples reportes) - rápido pero no escalable
2. **Largo plazo:** Implementar Opción 1 (Power BI Embedded) - profesional y seguro

## 📝 Siguiente Paso

**Dime cuál opción prefieres** y te ayudo a configurarla paso a paso:

- **Opción 1:** Tengo/puedo obtener Azure + Power BI Pro → Te ayudo con Embedded
- **Opción 2:** Quiero usar RLS → Te guío con Row-Level Security
- **Opción 3:** Necesito algo rápido → Configuramos múltiples reportes

## 🔍 Información de tu Reporte Actual

De tu URL extraje:
- **Report Key:** `63a87081-9083-404b-86e6-8067672b46af`
- **Tenant ID:** `6fd48f41-af81-45a5-9c1e-e3990bc27e7c`
- **Tipo:** Publish to Web (público, sin autenticación)

---

## 📞 ¿Necesitas ayuda?

Responde indicando:
1. ¿Tienes suscripción de Azure? (Sí/No)
2. ¿Tienes Power BI Pro o Premium? (Sí/No)
3. ¿Cuántas tiendas tienes? (para evaluar si múltiples reportes es viable)
