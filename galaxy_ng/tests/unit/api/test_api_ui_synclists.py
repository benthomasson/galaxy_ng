import logging

from rest_framework import status as http_code

from pulp_ansible.app import models as pulp_ansible_models

from galaxy_ng.app.constants import DeploymentMode
from galaxy_ng.app import models as galaxy_models
from galaxy_ng.app.models import auth as auth_models

from .base import BaseTestCase, get_current_ui_url

log = logging.getLogger(__name__)


class TestUiSynclistViewSet(BaseTestCase):
    default_owner_permissions = [
        'change_synclist',
        'view_synclist',
        'delete_synclist'
    ]

    def setUp(self):
        super().setUp()
        self.admin_user = auth_models.User.objects.create(username='admin')
        self.pe_group = self._create_partner_engineer_group()
        self.admin_user.groups.add(self.pe_group)
        self.admin_user.save()

        self.synclists_url = get_current_ui_url('synclists-list')
        self.group1 = auth_models.Group.objects.create(name='test1_group')
        self.user1 = auth_models.User.objects.create_user(username="test1", password="test1-secret")
        self.user1.groups.add(self.group1)
        self.user1.save()

    def _create_repository(self, name):
        repo = pulp_ansible_models.AnsibleRepository.objects.create(name='test_repo1')
        return repo

    def _create_synclist(
        self, name, repository, collections=None, namespaces=None,
        policy=None, groups=None,
    ):
        synclist = galaxy_models.SyncList.objects.create(name=name, repository=repository)
        if groups:
            groups_to_add = {}
            for group in groups:
                groups_to_add[group] = self.default_owner_permissions
            synclist.groups = groups_to_add
        return synclist

    def test_synclist_create_as_user(self):
        repo = self._create_repository('test_post_repo')
        repo.save()

        synclist_name = 'test_synclist_post'
        post_data = {
            'name': synclist_name,
            'repository': repo.pulp_id,
            'collections': [],
            'namespaces': [],
            'policy': 'whitelist',
            'groups': [],
        }

        self.client.force_authenticate(user=self.user)
        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            response = self.client.post(self.synclists_url, post_data, format='json')
            log.debug('response: %s', response)
            log.debug('response.data: %s', response.data)

            # should fail with auth now
            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            response = self.client.post(self.synclists_url, post_data, format='json')
            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

    def test_synclist_create_as_pe_group(self):
        repo = self._create_repository('test_post_repo')
        repo.save()

        synclist_name = 'test_synclist_post'
        post_data = {
            'name': synclist_name,
            'repository': repo.pulp_id,
            'collections': [],
            'namespaces': [],
            'policy': 'whitelist',
            'groups': [],
        }

        self.client.force_authenticate(user=self.admin_user)
        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            response = self.client.post(self.synclists_url, post_data, format='json')
            log.debug('response: %s', response)

            # should fail with auth now
            self.assertEqual(response.status_code, http_code.HTTP_201_CREATED)
            log.debug('response.data: %s', response.data)

            self.assertIn('name', response.data)
            self.assertIn('repository', response.data)
            self.assertEqual(response.data['name'], synclist_name)

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            response = self.client.post(self.synclists_url, post_data, format='json')
            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

    def test_synclist_update_as_pe_group_user(self):
        repo = self._create_repository('test_post_repo')
        repo.save()
        synclist1 = self._create_synclist(name='test_synclist_patch',
                                          repository=repo)

        synclist1.save()

        ns1_name = "unittestnamespace1"
        ns2_name = "unittestnamespace2"
        ns1 = self._create_namespace(ns1_name, groups=[self.pe_group])
        ns2 = self._create_namespace(ns2_name, groups=[self.pe_group])
        ns1.save()
        ns2.save()

        synclist_name = 'test_synclist_patch'
        post_data = {
            'name': synclist_name,
            'repository': repo.pulp_id,
            'collections': [],
            'namespaces': [ns1_name, ns2_name],
            'policy': 'whitelist',
            'groups': [{
                'name': self.pe_group.name,
                'id': self.pe_group.id,
                'object_permissions': self.default_owner_permissions
            }],
        }

        synclists_detail_url = get_current_ui_url(
            'synclists-detail',
            kwargs={"pk": synclist1.id})
        self.client.force_authenticate(user=self.admin_user)
        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            # should fail with auth now
            response = self.client.patch(synclists_detail_url, post_data, format='json')
            log.debug('response: %s', response)

            self.assertEqual(response.status_code, http_code.HTTP_200_OK)
            log.debug('response.data: %s', response.data)

            self.assertIn('name', response.data)
            self.assertIn('repository', response.data)
            self.assertEqual(response.data['name'], synclist_name)
            self.assertEqual(response.data['policy'], "whitelist")
            self.assertEqual(self.pe_group.name, response.data['groups'][0]['name'])

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            response = self.client.patch(synclists_detail_url, post_data, format='json')
            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

    def test_synclist_update_as_non_pe_group_user(self):
        repo = self._create_repository('test_post_repo')
        repo.save()
        synclist1 = self._create_synclist(name='test_synclist_patch',
                                          repository=repo)

        synclist1.save()

        ns1_name = "unittestnamespace1"
        ns2_name = "unittestnamespace2"
        ns1 = self._create_namespace(ns1_name, groups=[self.pe_group])
        ns2 = self._create_namespace(ns2_name, groups=[self.pe_group])
        ns1.save()
        ns2.save()

        synclist_name = 'test_synclist_patch'
        post_data = {
            'name': synclist_name,
            'repository': repo.pulp_id,
            'collections': [],
            'namespaces': [ns1_name, ns2_name],
            'policy': 'whitelist',
            'groups': [self.group1.name],
        }

        synclists_detail_url = get_current_ui_url(
            'synclists-detail',
            kwargs={"pk": synclist1.id})
        self.client.force_authenticate(user=self.user1)

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            # should fail with auth now
            response = self.client.patch(synclists_detail_url, post_data, format='json')
            log.debug('response: %s', response)

            log.debug('response.data: %s', response.data)
            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            response = self.client.patch(synclists_detail_url, post_data, format='json')
            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

    def test_synclist_list_no_auth(self):
        self.client.force_authenticate(user=None)
        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            response = self.client.get(self.synclists_url)
            log.debug('response: %s', response)

            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            response = self.client.get(self.synclists_url)
            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

    def test_synclist_list_as_non_pe_group_user(self):
        self.client.force_authenticate(user=self.user1)
        repo1 = self._create_repository(name="test_repo1")
        synclist1 = self._create_synclist(name='test_synclist1',
                                          repository=repo1)

        synclist1.save()

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            response = self.client.get(self.synclists_url)
            log.debug('response.data: %s', response.data)
            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            response = self.client.get(self.synclists_url)
            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

    def test_synclist_list_as_pe_group_user(self):
        self.client.force_authenticate(user=self.admin_user)
        repo1 = self._create_repository(name="test_repo1")
        synclist1 = self._create_synclist(name='test_synclist1',
                                          repository=repo1)

        synclist1.save()

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            response = self.client.get(self.synclists_url)
            log.debug('response.data: %s', response.data)
            self.assertEqual(response.status_code, http_code.HTTP_200_OK)

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            response = self.client.get(self.synclists_url)
            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

    def test_synclist_list_empty(self):
        # self.client.force_authenticate(user=self.user)

        self.client.force_authenticate(user=self.admin_user)
        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            response = self.client.get(self.synclists_url)
            self.assertEqual(response.status_code, http_code.HTTP_200_OK)
            data = response.data['data']
            # self.assertEqual(len(data), auth_models.User.objects.all().count())
            log.debug('response(authed): %s', response)
            log.debug('data: %s', data)

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            response = self.client.get(self.synclists_url)
            self.assertEqual(response.status_code, http_code.HTTP_200_OK)
            log.debug('response(insights): %s', response)

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            response = self.client.get(self.synclists_url)
            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

    def test_synclist_detail_as_pe_group_user(self):
        self.client.force_authenticate(user=self.admin_user)
        repo1 = self._create_repository(name="test_repo1")
        synclist_name = 'test_synclist_post'
        synclist1 = self._create_synclist(name=synclist_name,
                                          repository=repo1)
        synclist1.save()
        synclists_detail_url = get_current_ui_url(
            'synclists-detail',
            kwargs={"pk": synclist1.id})

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            response = self.client.get(synclists_detail_url)

            self.assertEqual(response.status_code, http_code.HTTP_200_OK)
            log.debug('response.data: %s', response.data)

            data = response.data
            import pprint
            log.debug('data: %s', pprint.pformat(data))

            self.assertIn('name', response.data)
            self.assertIn('repository', response.data)
            self.assertEqual(response.data['name'], synclist_name)
            self.assertEqual(response.data['policy'], "blacklist")
            self.assertEqual(response.data['collections'], [])
            self.assertEqual(response.data['namespaces'], [])

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            response = self.client.get(synclists_detail_url)
            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

    def test_synclist_detail_as_non_pe_group_user(self):
        self.client.force_authenticate(user=self.user1)
        repo1 = self._create_repository(name="test_repo1")
        synclist_name = 'test_synclist_post'
        synclist1 = self._create_synclist(name=synclist_name,
                                          repository=repo1)
        synclist1.save()

        synclists_detail_url = get_current_ui_url(
            'synclists-detail',
            kwargs={"pk": synclist1.id})

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            response = self.client.get(synclists_detail_url)
            log.debug('response.data: %s', response.data)
            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            response = self.client.get(synclists_detail_url)
            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

    def test_synclist_delete_as_pe_group_user(self):
        self.client.force_authenticate(user=self.admin_user)
        repo1 = self._create_repository(name="test_repo1")
        synclist_name = 'test_synclist_post'
        synclist1 = self._create_synclist(name=synclist_name,
                                          repository=repo1)
        synclist1.save()
        synclists_detail_url = get_current_ui_url(
            'synclists-detail',
            kwargs={"pk": synclist1.id})

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            log.debug('delete url: %s', synclists_detail_url)

            response = self.client.delete(synclists_detail_url)
            log.debug('delete response: %s', response)

            self.assertEqual(response.status_code, http_code.HTTP_204_NO_CONTENT)

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            response = self.client.delete(synclists_detail_url)
            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

    def test_synclist_delete_as_non_pe_group_user(self):
        self.client.force_authenticate(user=self.user1)
        repo1 = self._create_repository(name="test_repo1")
        synclist_name = 'test_synclist_post'
        synclist1 = self._create_synclist(name=synclist_name,
                                          repository=repo1)
        synclist1.save()
        synclists_detail_url = get_current_ui_url(
            'synclists-detail',
            kwargs={"pk": synclist1.id})

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            log.debug('delete url: %s', synclists_detail_url)

            response = self.client.delete(synclists_detail_url)
            log.debug('delete response: %s', response)

            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            response = self.client.delete(synclists_detail_url)
            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)
