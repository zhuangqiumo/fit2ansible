import os
import uuid
import yaml

from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.models import JsonTextField
from ansible_api.models import Project, Host, Group, Playbook
from ansible_api.models.mixins import (
    AbstractProjectResourceModel, AbstractExecutionModel
)
from ansible_api.ctx import set_current_project
from ansible_api.signals import pre_execution_start, post_execution_start


__all__ = ['Package', 'Cluster', 'Node', 'Role', 'DeployExecution']


# 离线包的model
class Package(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=20, unique=True, verbose_name=_('Name'))
    meta = JsonTextField(blank=True, null=True, verbose_name=_('Meta'))
    date_created = models.DateTimeField(auto_now_add=True, verbose_name=_('Date created'))

    packages_dir = os.path.join(settings.BASE_DIR, 'data', 'packages')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('Package')

    @classmethod
    def lookup(cls):
        for d in os.listdir(cls.packages_dir):
            full_path = os.path.join(cls.packages_dir, d)
            meta_path = os.path.join(full_path, 'meta.yml')
            if not os.path.isdir(full_path) or not os.path.isfile(meta_path):
                continue
            with open(meta_path) as f:
                metadata = yaml.load(f)
            defaults = {'name': d, 'meta': metadata}
            cls.objects.update_or_create(defaults=defaults, name=d)


class Cluster(Project):
    package = models.ForeignKey("Package", null=True, on_delete=models.SET_NULL)
    template = models.CharField(max_length=64, blank=True, default='')

    def create_roles(self):
        set_current_project(self)
        _roles = {}
        for role in self.package.meta.get('roles', []):
            _roles[role['name']] = role
        template = None
        for tmp in self.package.meta.get('templates', []):
            if tmp['name'] == self.template:
                template = tmp
                break
        for role in template.get('roles', []):
            _roles[role['name']] = role
        roles_data = [role for role in _roles.values()]

        children_data = {}
        for data in roles_data:
            children_data[data['name']] = data.pop('children', [])
            Role.objects.update_or_create(defaults=data, name=data['name'])

        for name, children_name in children_data.items():
            try:
                role = Role.objects.get(name=name)
                children = Role.objects.filter(name__in=children_name)
                role.children.set(children)
            except Role.DoesNotExist:
                pass


class Node(Host):
    class Meta:
        proxy = True

    @property
    def roles(self):
        return self.groups

    @roles.setter
    def roles(self, value):
        self.groups.set(value)

    def add_vars(self, _vars):
        __vars = {k: v for k, v in self.vars.items()}
        __vars.update(_vars)
        if self.vars != __vars:
            self.vars = __vars
            self.save()

    def remove_var(self, key):
        __vars = self.vars
        if key in __vars:
            del __vars[key]
            self.vars = __vars
            self.save()

    @classmethod
    def create_localhost(cls):
        cls.objects.create(name="localhost", vars={"ansible_connection": "local"})

    def get_var(self, key, default):
        return self.vars.get(key, default)

    def get_node_group_label(self):
        return self.get_var("openshift_node_group_name", "-").split('-')[-1]


class Role(Group):
    class Meta:
        proxy = True

    @property
    def nodes(self):
        return self.hosts

    @nodes.setter
    def nodes(self, value):
        self.hosts.set(value)

    def __str__(self):
        return "%s %s" % (self.project, self.name)


class DeployExecution(AbstractProjectResourceModel, AbstractExecutionModel):
    project = models.ForeignKey('Cluster', on_delete=models.CASCADE)
    package = models.ForeignKey('Package', on_delete=models.CASCADE)

    def start(self):
        result = {"raw": {}, "summary": {}}
        pre_execution_start.send(self.__class__, execution=self)
        for playbook in self.project.playbook_set.all():
            _result = playbook.execute()
            result["summary"].update(_result["summary"])
            if not _result.get('summary', {}).get('success', False):
                break
        post_execution_start.send(self.__class__, execution=self, result=result)
        return result


