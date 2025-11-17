import uuid
import random

# IDs de las tiendas generadas anteriormente
tiendas = [
    ('c35a72ab-5ddc-40e2-b442-56a8871a3010', 'Tienda 1'),
    ('0e924614-681a-4cd9-a303-b6d485d2fefd', 'Tienda 2'),
    ('9bf7babe-0c62-4d04-8e8b-fdd1764d76f8', 'Tienda 3'),
    ('87d5dd8f-34e4-4b38-977c-26a3dff4450d', 'Tienda 4'),
    ('6d4def82-65bc-44d1-8de2-907fce696010', 'Tienda 5'),
    ('8bbfbc46-aa31-4d2e-93b5-006f3a9690e7', 'Tienda 6'),
]

# Categorías por tienda
categorias_nombres = [
    'Electrónica',
    'Ropa',
    'Alimentos',
    'Bebidas',
    'Hogar',
    'Deportes'
]

# Productos por categoría
productos_por_categoria = {
    'Electrónica': [
        ('Auriculares Bluetooth', 25000, 15000, 15, 'Auriculares inalámbricos con cancelación de ruido'),
        ('Mouse Gaming', 18000, 10000, 20, 'Mouse óptico para gaming con RGB'),
        ('Teclado Mecánico', 45000, 28000, 8, 'Teclado mecánico RGB con switches azules'),
        ('Webcam HD', 35000, 22000, 12, 'Cámara web Full HD 1080p'),
        ('Cable USB-C', 5000, 2000, 50, 'Cable USB tipo C de 2 metros'),
    ],
    'Ropa': [
        ('Polera Básica', 8000, 4000, 30, 'Polera de algodón 100%'),
        ('Jeans Clásicos', 25000, 15000, 15, 'Pantalón jean corte clásico'),
        ('Zapatillas Deportivas', 35000, 20000, 12, 'Zapatillas para running'),
        ('Chaqueta Invierno', 45000, 28000, 8, 'Chaqueta térmica para invierno'),
        ('Gorro Lana', 6000, 3000, 25, 'Gorro tejido de lana'),
    ],
    'Alimentos': [
        ('Arroz 1kg', 1500, 800, 40, 'Arroz grado 1 bolsa de 1kg'),
        ('Aceite 1L', 3500, 2000, 25, 'Aceite vegetal botella de 1 litro'),
        ('Fideos 500g', 1200, 600, 50, 'Fideos espagueti pack 500g'),
        ('Azúcar 1kg', 1800, 900, 30, 'Azúcar refinada bolsa de 1kg'),
        ('Sal 1kg', 800, 400, 45, 'Sal de mesa bolsa de 1kg'),
    ],
    'Bebidas': [
        ('Coca Cola 1.5L', 1800, 1000, 35, 'Bebida gaseosa Coca Cola 1.5 litros'),
        ('Agua Mineral 500ml', 800, 400, 60, 'Agua mineral sin gas'),
        ('Jugo Natural 1L', 2500, 1400, 20, 'Jugo de naranja natural'),
        ('Energética 250ml', 1500, 800, 40, 'Bebida energética lata 250ml'),
        ('Té Helado 500ml', 1200, 600, 30, 'Té helado sabor limón'),
    ],
    'Hogar': [
        ('Escobillón', 5000, 2500, 15, 'Escobillón con palo telescópico'),
        ('Detergente 1L', 3500, 2000, 25, 'Detergente líquido multiuso'),
        ('Toalla Baño', 12000, 7000, 10, 'Toalla de baño 100% algodón'),
        ('Frazada', 18000, 10000, 8, 'Frazada polar tamaño queen'),
        ('Velas Aromáticas', 4000, 2000, 20, 'Set de 3 velas aromáticas'),
    ],
    'Deportes': [
        ('Pelota Fútbol', 15000, 9000, 12, 'Pelota de fútbol número 5'),
        ('Pesas 5kg', 18000, 11000, 8, 'Par de pesas de 5kg cada una'),
        ('Cuerda Saltar', 4000, 2000, 20, 'Cuerda para saltar ajustable'),
        ('Colchoneta Yoga', 12000, 7000, 10, 'Colchoneta para yoga y ejercicios'),
        ('Botella Deportiva', 6000, 3000, 25, 'Botella deportiva 750ml'),
    ],
}

print("=== SQL PARA CREAR CATEGORÍAS Y PRODUCTOS ===")
print()

for id_store, nombre_tienda in tiendas:
    print(f"-- ========================================")
    print(f"-- {nombre_tienda}")
    print(f"-- ========================================")
    print()
    
    # Crear categorías para esta tienda
    categorias_ids = {}
    for categoria_nombre in categorias_nombres:
        categoria_id = str(uuid.uuid4())
        categorias_ids[categoria_nombre] = categoria_id
        
        print(f"-- Categoría: {categoria_nombre}")
        print(f"INSERT INTO category (id_category, name_category, id_store)")
        print(f"VALUES ('{categoria_id}', '{categoria_nombre}', '{id_store}');")
        print()
    
    print()
    
    # Crear productos para esta tienda
    productos_generados = []
    
    for categoria_nombre, productos in productos_por_categoria.items():
        categoria_id = categorias_ids[categoria_nombre]
        
        # Tomar 2 productos aleatorios de cada categoría (total: 6 categorías x 2 = 12 productos)
        productos_seleccionados = random.sample(productos, min(2, len(productos)))
        
        for producto_nombre, precio_venta, precio_compra, stock, descripcion in productos_seleccionados:
            producto_id = str(uuid.uuid4())
            
            # Generar variación en precios y stock para cada tienda
            precio_venta_var = precio_venta + random.randint(-1000, 1000)
            precio_compra_var = precio_compra + random.randint(-500, 500)
            stock_var = stock + random.randint(-5, 10)
            
            # Asegurar que el stock no sea negativo
            stock_var = max(0, stock_var)
            
            # Algunos productos con stock bajo para probar alertas
            if random.random() < 0.2:  # 20% de productos con stock bajo
                stock_var = random.randint(0, 9)
            
            print(f"-- Producto: {producto_nombre} ({categoria_nombre})")
            print(f"INSERT INTO products (id_product, name, price_sale, stock, description, image, id_store, price_buy, category, status_product)")
            print(f"VALUES ('{producto_id}', '{producto_nombre}', {precio_venta_var}, {stock_var}, '{descripcion}', '\\x'::bytea, '{id_store}', {precio_compra_var}, '{categoria_nombre}', TRUE);")
            print()
            
            productos_generados.append(producto_nombre)
    
    print(f"-- Total productos creados para {nombre_tienda}: {len(productos_generados)}")
    print()
    print()

print()
print("=== RESUMEN ===")
print(f"Total de tiendas: {len(tiendas)}")
print(f"Categorías por tienda: {len(categorias_nombres)}")
print(f"Productos por tienda: ~12 (2 por categoría)")
print(f"Total de productos: ~{len(tiendas) * 12}")
print()
print("Categorías creadas:")
for cat in categorias_nombres:
    print(f"  - {cat}")
print()
print("NOTA: Algunos productos tienen stock bajo (<10) para probar el sistema de alertas por email.")
