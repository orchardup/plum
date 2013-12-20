from plum import Service
from .testcases import DockerClientTestCase


class ServiceTest(DockerClientTestCase):
    def test_name_validations(self):
        self.assertRaises(ValueError, lambda: Service(name=''))

        self.assertRaises(ValueError, lambda: Service(name=' '))
        self.assertRaises(ValueError, lambda: Service(name='/'))
        self.assertRaises(ValueError, lambda: Service(name='!'))
        self.assertRaises(ValueError, lambda: Service(name='\xe2'))
        self.assertRaises(ValueError, lambda: Service(name='_'))
        self.assertRaises(ValueError, lambda: Service(name='____'))
        self.assertRaises(ValueError, lambda: Service(name='foo_bar'))
        self.assertRaises(ValueError, lambda: Service(name='__foo_bar__'))

        Service('a')
        Service('foo')

    def test_project_validation(self):
        self.assertRaises(ValueError, lambda: Service(name='foo', project='_'))
        Service(name='foo', project='bar')

    def test_containers(self):
        foo = self.create_service('foo')
        bar = self.create_service('bar')

        foo.start()

        self.assertEqual(len(foo.containers()), 1)
        self.assertEqual(foo.containers()[0].name, '/default_foo_1')
        self.assertEqual(len(bar.containers()), 0)

        bar.scale(2)

        self.assertEqual(len(foo.containers()), 1)
        self.assertEqual(len(bar.containers()), 2)

        names = [c.name for c in bar.containers()]
        self.assertIn('/default_bar_1', names)
        self.assertIn('/default_bar_2', names)

    def test_containers_one_off(self):
        db = self.create_service('db')
        container = db.create_container(one_off=True)
        self.assertEqual(db.containers(stopped=True), [])
        self.assertEqual(db.containers(one_off=True, stopped=True), [container])

    def test_project_is_added_to_container_name(self):
        service = self.create_service('web', project='myproject')
        service.start()
        self.assertEqual(service.containers()[0].name, '/myproject_web_1')

    def test_up_scale_down(self):
        service = self.create_service('scalingtest')
        self.assertEqual(len(service.containers()), 0)

        service.start()
        self.assertEqual(len(service.containers()), 1)

        service.start()
        self.assertEqual(len(service.containers()), 1)

        service.scale(2)
        self.assertEqual(len(service.containers()), 2)

        service.scale(1)
        self.assertEqual(len(service.containers()), 1)

        service.stop()
        self.assertEqual(len(service.containers()), 0)

        service.stop()
        self.assertEqual(len(service.containers()), 0)

    def test_create_container_with_one_off(self):
        db = self.create_service('db')
        container = db.create_container(one_off=True)
        self.assertEqual(container.name, '/default_db_run_1')

    def test_create_container_with_one_off_when_existing_container_is_running(self):
        db = self.create_service('db')
        db.start()
        container = db.create_container(one_off=True)
        self.assertEqual(container.name, '/default_db_run_1')

    def test_start_container_passes_through_options(self):
        db = self.create_service('db')
        db.start_container(environment={'FOO': 'BAR'})
        self.assertEqual(db.containers()[0].environment['FOO'], 'BAR')

    def test_start_container_inherits_options_from_constructor(self):
        db = self.create_service('db', environment={'FOO': 'BAR'})
        db.start_container()
        self.assertEqual(db.containers()[0].environment['FOO'], 'BAR')

    def test_start_container_creates_links(self):
        db = self.create_service('db')
        web = self.create_service('web', links=[db])
        db.start_container()
        web.start_container()
        self.assertIn('default_db_1', web.containers()[0].links())
        db.stop()
        web.stop()

    def test_start_container_builds_images(self):
        service = Service(
            name='test',
            client=self.client,
            build='tests/fixtures/simple-dockerfile',
        )
        container = service.start()
        container.wait()
        self.assertIn('success', container.logs())

    def test_start_container_creates_ports(self):
        service = self.create_service('web', ports=[8000])
        container = service.start_container().inspect()
        self.assertIn('8000/tcp', container['HostConfig']['PortBindings'])
        self.assertNotEqual(container['HostConfig']['PortBindings']['8000/tcp'][0]['HostPort'], '8000')

    def test_start_container_creates_fixed_external_ports(self):
        service = self.create_service('web', ports=['8000:8000'])
        container = service.start_container().inspect()
        self.assertIn('8000/tcp', container['HostConfig']['PortBindings'])
        self.assertEqual(container['HostConfig']['PortBindings']['8000/tcp'][0]['HostPort'], '8000')


