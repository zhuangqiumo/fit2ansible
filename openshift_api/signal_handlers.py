from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver

from .models import Role, Package, Cluster


@receiver(post_save, sender=Cluster)
def on_cluster_save(sender, instance=None, **kwargs):
    if instance and instance.template:
        instance.create_roles()


def auto_lookup_packages():
    Package.lookup()


auto_lookup_packages()
