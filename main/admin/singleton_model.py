from django.db import models



class SingletonModel(models.Model):
    class Meta:
        abstract = True
 
    def save(self, *args, **kwargs):
        self.__class__.objects.exclude(id=self.id).delete()
        super(SingletonModel, self).save(*args, **kwargs)
 
    @classmethod
    def get_solo(cls):
        """ Возвращает единственный объект или создает новый """
        obj, created = cls.objects.get_or_create()
        return obj
