import uuid
import random
from datetime import datetime, timedelta

# IDs de las tiendas
tiendas = [
    ('c35a72ab-5ddc-40e2-b442-56a8871a3010', 'Tienda 1'),
    ('0e924614-681a-4cd9-a303-b6d485d2fefd', 'Tienda 2'),
    ('9bf7babe-0c62-4d04-8e8b-fdd1764d76f8', 'Tienda 3'),
    ('87d5dd8f-34e4-4b38-977c-26a3dff4450d', 'Tienda 4'),
    ('6d4def82-65bc-44d1-8de2-907fce696010', 'Tienda 5'),
    ('8bbfbc46-aa31-4d2e-93b5-006f3a9690e7', 'Tienda 6'),
]

# Métodos de pago
metodos_pago = ['Efectivo', 'Tarjeta Débito', 'Tarjeta Crédito', 'Transferencia']

# Rango de fechas: último mes
fecha_fin = datetime.now().date()
fecha_inicio = fecha_fin - timedelta(days=30)

print("=== SQL PARA CREAR VENTAS Y SALES_BAG ===")
print()
print(f"-- Generando ventas desde {fecha_inicio} hasta {fecha_fin}")
print()

# Primero, obtener los productos de cada tienda (asumiendo que ya fueron creados)
# Nota: Este script asume que ya ejecutaste el script de productos
print("-- IMPORTANTE: Antes de ejecutar este SQL, debes tener los productos creados.")
print("-- Este script usa consultas para obtener productos existentes de cada tienda.")
print()

total_ventas = 0

for id_store, nombre_tienda in tiendas:
    print(f"-- ========================================")
    print(f"-- {nombre_tienda} - 20 VENTAS")
    print(f"-- ========================================")
    print()
    
    # Generar 20 ventas para esta tienda
    for i in range(1, 21):
        # Fecha aleatoria en el rango de 30 días
        dias_aleatorios = random.randint(0, 30)
        fecha_venta = fecha_inicio + timedelta(days=dias_aleatorios)
        
        # Método de pago aleatorio
        metodo_pago = random.choice(metodos_pago)
        
        # ID de la venta
        id_sale = str(uuid.uuid4())
        
        # Cantidad de productos en esta venta (1-5 productos)
        num_productos = random.randint(1, 5)
        
        # Cantidad de items y total (se calcularán después)
        print(f"-- Venta {i} de {nombre_tienda} - {fecha_venta}")
        print(f"DO $$")
        print(f"DECLARE")
        print(f"    v_sale_id UUID := '{id_sale}';")
        print(f"    v_store_id UUID := '{id_store}';")
        print(f"    v_productos UUID[];")
        print(f"    v_producto_id UUID;")
        print(f"    v_price DECIMAL;")
        print(f"    v_cantidad INTEGER;")
        print(f"    v_total DECIMAL := 0;")
        print(f"    v_items DECIMAL := 0;")
        print(f"    v_utility DECIMAL := 0;")
        print(f"    v_price_buy DECIMAL;")
        print(f"BEGIN")
        print(f"    -- Obtener productos aleatorios de esta tienda")
        print(f"    SELECT ARRAY(")
        print(f"        SELECT id_product FROM products ")
        print(f"        WHERE id_store = v_store_id AND status_product = TRUE ")
        print(f"        ORDER BY RANDOM() LIMIT {num_productos}")
        print(f"    ) INTO v_productos;")
        print(f"    ")
        print(f"    -- Insertar la venta (se actualizará después)")
        print(f"    INSERT INTO sales (id_sale, date_sale, items, total, pay_method, state, utility, id_store)")
        print(f"    VALUES (v_sale_id, '{fecha_venta}', 0, 0, '{metodo_pago}', TRUE, 0, v_store_id);")
        print(f"    ")
        print(f"    -- Insertar productos en sales_bag y calcular totales")
        print(f"    FOREACH v_producto_id IN ARRAY v_productos")
        print(f"    LOOP")
        print(f"        -- Cantidad aleatoria (1-5 unidades)")
        print(f"        v_cantidad := (RANDOM() * 4 + 1)::INTEGER;")
        print(f"        ")
        print(f"        -- Obtener precio de venta y compra del producto")
        print(f"        SELECT price_sale, price_buy INTO v_price, v_price_buy")
        print(f"        FROM products WHERE id_product = v_producto_id;")
        print(f"        ")
        print(f"        -- Insertar en sales_bag")
        print(f"        INSERT INTO sales_bag (id_sale, id_product, quantitity)")
        print(f"        VALUES (v_sale_id, v_producto_id, v_cantidad);")
        print(f"        ")
        print(f"        -- Acumular totales")
        print(f"        v_items := v_items + v_cantidad;")
        print(f"        v_total := v_total + (v_price * v_cantidad);")
        print(f"        v_utility := v_utility + ((v_price - v_price_buy) * v_cantidad);")
        print(f"    END LOOP;")
        print(f"    ")
        print(f"    -- Actualizar la venta con los totales calculados")
        print(f"    UPDATE sales")
        print(f"    SET items = v_items, total = v_total, utility = v_utility")
        print(f"    WHERE id_sale = v_sale_id;")
        print(f"    ")
        print(f"    RAISE NOTICE 'Venta % creada: % items, Total: $%', v_sale_id, v_items, v_total;")
        print(f"END $$;")
        print()
        
        total_ventas += 1
    
    print()

print()
print("=== RESUMEN ===")
print(f"Total de tiendas: {len(tiendas)}")
print(f"Ventas por tienda: 20")
print(f"Total de ventas: {total_ventas}")
print(f"Rango de fechas: {fecha_inicio} a {fecha_fin}")
print(f"Productos por venta: 1-5 (aleatorio)")
print(f"Cantidad por producto: 1-5 unidades (aleatorio)")
print(f"Métodos de pago: {', '.join(metodos_pago)}")
print()
print("NOTA: Este script usa bloques DO $$ con lógica PL/pgSQL para:")
print("  1. Seleccionar productos aleatorios de cada tienda")
print("  2. Crear la venta con items y totales calculados")
print("  3. Insertar productos en sales_bag")
print("  4. Calcular utility (ganancia) automáticamente")
