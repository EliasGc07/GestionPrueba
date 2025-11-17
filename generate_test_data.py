import bcrypt
import uuid

def hash_password(password):
    """Hashea una contraseña usando bcrypt"""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

# Generar contraseñas hasheadas
admin_password = hash_password("admin123")
user_password = hash_password("user123")

print("=== CONTRASEÑAS HASHEADAS ===")
print(f"Admin password (admin123): {admin_password}")
print(f"User password (user123): {user_password}")
print()

# Generar UUIDs para las tiendas
tiendas = []
for i in range(1, 7):
    tiendas.append({
        'id': str(uuid.uuid4()),
        'nombre': f'Tienda {i}',
        'direccion': f'Calle Principal {i*100}, Santiago',
        'telefono': f'+56912345{i:03d}',
        'admin_nombre': f'Administrador Tienda {i}'
    })

print("=== SQL PARA CREAR 6 TIENDAS ===")
print()
for tienda in tiendas:
    print(f"-- Tienda: {tienda['nombre']}")
    print(f"INSERT INTO stores (id_store, name, direction, phone, administrator_name, id_sale)")
    print(f"VALUES ('{tienda['id']}', '{tienda['nombre']}', '{tienda['direccion']}', '{tienda['telefono']}', '{tienda['admin_nombre']}', NULL);")
    print()

print()
print("=== SQL PARA CREAR USUARIOS (2 POR TIENDA: 1 ADMIN + 1 USUARIO) ===")
print()

email = "el.nico.taz36@gmail.com"

for idx, tienda in enumerate(tiendas, 1):
    # Usuario Admin
    admin_user_id = str(uuid.uuid4())
    admin_info_id = str(uuid.uuid4())
    admin_username = f"admin{idx}"
    
    print(f"-- Usuario Admin de {tienda['nombre']}")
    print(f"INSERT INTO users (id_user, id_store, username, password, type_user, state_user)")
    print(f"VALUES ('{admin_user_id}', '{tienda['id']}', '{admin_username}', '{admin_password}', TRUE, TRUE);")
    print()
    print(f"INSERT INTO users_info (id_user_info, id_user, name, email, rut, born_date)")
    print(f"VALUES ('{admin_info_id}', '{admin_user_id}', 'Admin {tienda['nombre']}', '{email}', '12345678-{idx}', '1990-01-{idx:02d}');")
    print()
    
    # Usuario Normal
    user_user_id = str(uuid.uuid4())
    user_info_id = str(uuid.uuid4())
    user_username = f"usuario{idx}"
    
    print(f"-- Usuario Normal de {tienda['nombre']}")
    print(f"INSERT INTO users (id_user, id_store, username, password, type_user, state_user)")
    print(f"VALUES ('{user_user_id}', '{tienda['id']}', '{user_username}', '{user_password}', FALSE, TRUE);")
    print()
    print(f"INSERT INTO users_info (id_user_info, id_user, name, email, rut, born_date)")
    print(f"VALUES ('{user_info_id}', '{user_user_id}', 'Usuario {tienda['nombre']}', '{email}', '87654321-{idx}', '1995-01-{idx:02d}');")
    print()
    print()

print("=== RESUMEN DE CREDENCIALES ===")
print()
print("ADMINISTRADORES:")
for i in range(1, 7):
    print(f"  Username: admin{i} | Password: admin123")
print()
print("USUARIOS NORMALES:")
for i in range(1, 7):
    print(f"  Username: usuario{i} | Password: user123")
print()
print(f"Todos los usuarios tienen el email: {email}")
