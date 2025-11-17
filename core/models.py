from django.db import models
import uuid
from threading import Thread


# Modelo de SuperAdmin
class SuperAdmin(models.Model):
    username = models.TextField(primary_key=True)
    password = models.TextField()

    class Meta:
        managed = False
        db_table = 'super_admin'
    
    def __str__(self):
        return self.username


# Tiendas
class Stores(models.Model):
    id_store = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.TextField()
    direction = models.TextField()
    phone = models.TextField()
    administrator_name = models.TextField()

    class Meta:
        managed = False
        db_table = 'stores'
    
    def __str__(self):
        return self.name


# Modelo de Categorías
class Category(models.Model):
    id_category = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name_category = models.TextField()
    id_store = models.ForeignKey(Stores, models.DO_NOTHING, db_column='id_store')

    class Meta:
        managed = False
        db_table = 'category'
    
    def __str__(self):
        return self.name_category


# Modelo de Usuarios
class Users(models.Model):
    id_user = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    id_store = models.ForeignKey(Stores, models.DO_NOTHING, db_column='id_store', blank=True, null=True)
    username = models.TextField()
    password = models.TextField()
    type_user = models.BooleanField()
    state_user = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'users'


# Información adicional de usuarios
class UsersInfo(models.Model):
    id_user_info = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    id_user = models.OneToOneField(Users, models.DO_NOTHING, db_column='id_user')
    name = models.TextField()
    email = models.TextField()
    rut = models.TextField()
    born_date = models.DateField()

    class Meta:
        managed = False
        db_table = 'users_info'
    
    def __str__(self):
        return self.name


# Modelo de Productos
class Products(models.Model):
    id_product = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.TextField()
    price_sale = models.DecimalField(max_digits=10, decimal_places=0)
    stock = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    image = models.BinaryField()
    id_store = models.ForeignKey(Stores, models.DO_NOTHING, db_column='id_store', blank=True, null=True)
    price_buy = models.DecimalField(max_digits=10, decimal_places=0)
    category = models.TextField()
    status_product = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'products'
    
    def __str__(self):
        return self.name
    
    def _enviar_alerta_asincrona(self, producto_name, stock_actual, store_name, to_email):
        """Función auxiliar para enviar email en segundo plano"""
        from .notifications import enviar_alerta_stock_bajo
        import time
        
        # Respetar límite de Resend: 2 requests/segundo
        time.sleep(0.6)  # Esperar 600ms entre emails
        
        enviar_alerta_stock_bajo(producto_name, stock_actual, store_name, to_email)
    
    def save(self, *args, **kwargs):
        """
        Sobrescribe el método save para enviar alertas automáticas 
        cuando el stock está bajo (de forma asíncrona para no bloquear)
        """
        if not self.id_product:
            self.id_product = uuid.uuid4()
        # Extraer user_id si viene en kwargs
        user_id = kwargs.pop('user_id', None)
        
        # Si es una actualización (no una creación)
        if self.pk:
            # Obtener el producto anterior de la BD
            try:
                old_product = Products.objects.get(pk=self.pk)
                old_stock = float(old_product.stock)
                new_stock = float(self.stock)
                
                # Solo enviar alerta si el stock cambió y está bajo
                if old_stock != new_stock and new_stock < 10:
                    # Obtener el email del usuario logueado desde la sesión
                    user_email = None
                    
                    if user_id:
                        try:
                            # Buscar el email en UsersInfo usando el user_id
                            user_info = UsersInfo.objects.get(id_user=user_id)
                            user_email = user_info.email
                        except UsersInfo.DoesNotExist:
                            # Si no se encuentra, usar email de prueba
                            user_email = "el.nico.taz36@gmail.com"
                    else:
                        # Si no hay user_id, usar email de prueba
                        user_email = "el.nico.taz36@gmail.com"
                    
                    # Enviar email en segundo plano
                    thread = Thread(
                        target=self._enviar_alerta_asincrona,
                        args=(self.name, int(new_stock), self.id_store.name, user_email)
                    )
                    thread.daemon = True
                    thread.start()
            
            except Products.DoesNotExist:
                pass  # Es una creación, no una actualización
        
        # Guardar normalmente (sin esperar al envío de email)
        super().save(*args, **kwargs)


# Modelo de Ventas
class Sales(models.Model):
    id_sale = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date_sale = models.DateField()
    items = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    pay_method = models.TextField()
    state = models.BooleanField(default=True)
    utility = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    id_store = models.ForeignKey(Stores, models.DO_NOTHING, db_column='id_store', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'sales'
    
    def __str__(self):
        return f"Venta {self.id_sale} - {self.date_sale}"


# Bolsa de Ventas (productos vendidos en cada venta)
class SalesBag(models.Model):
    id_sales_bag = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    id_sale = models.ForeignKey(Sales, models.DO_NOTHING, db_column='id_sale')
    id_product = models.ForeignKey(Products, models.DO_NOTHING, db_column='id_product')
    quantitity = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'sales_bag'
    
    def __str__(self):
        return f"Bolsa {self.id_sales_bag}"


# Movimientos de Ventas (auditoría)
class SalesMovement(models.Model):
    id_movement = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    type_movement = models.TextField()
    type_action = models.TextField()
    date_movement = models.DateTimeField()
    id_sale = models.ForeignKey(Sales, models.DO_NOTHING, db_column='id_sale', blank=True, null=True)
    id_product = models.ForeignKey(Products, models.DO_NOTHING, db_column='id_product', blank=True, null=True)
    id_user = models.ForeignKey(Users, models.DO_NOTHING, db_column='id_user')

    class Meta:
        managed = False
        db_table = 'sales_movement'
    
    def __str__(self):
        return f"Movimiento {self.type_movement} - {self.date_movement}"

