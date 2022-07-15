import shutil
import tempfile


from django import forms
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.conf import settings
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from posts.models import Comment, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostUrlTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовая пост',
            image=uploaded
        )

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.author = User.objects.create_user(username='author')
        self.authorized_author = Client()
        self.authorized_author.force_login(self.author)
        self.templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            (reverse('posts:group_list',
                     kwargs={
                         'slug':
                             f'{self.group.slug}'})): 'posts/group_list.html',
            (reverse('posts:profile',
                     kwargs={
                         'username':
                             f'{self.post.author}'})): 'posts/profile.html',
            (reverse('posts:post_detail',
                     kwargs={
                         'post_id':
                             f'{self.post.id}'})): 'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/post_create.html',
            (reverse('posts:post_edit',
                     kwargs={'post_id':
                             f'{self.post.id}'})): 'posts/post_create.html'
        }


    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        for reverse_name, template in self.templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        post_object = response.context['page_obj'][0]
        task_text_0 = post_object.text
        task_group = post_object.group
        task_image = post_object.image
        self.assertEqual(task_text_0, self.post.text)
        self.assertEqual(task_group, self.post.group)
        self.assertEqual(task_image, self.post.image)

    def test_group_list_page_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = (self.authorized_client.
                    get(reverse('posts:group_list',
                                kwargs={'slug': 'test-slug'})))
        self.assertEqual(response.context.get('group').title,
                         'Тестовая группа')
        self.assertEqual(response.context.get('group').slug,
                         'test-slug')
        self.assertEqual(response.context.get('group').id, self.post.id)

    def test_profile_page_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = (self.authorized_client.
                    get(reverse('posts:profile',
                                kwargs={'username': 'author'})))
        self.assertEqual(response.context.get('user').username,
                         f'{self.post.author}')
        self.assertEqual(response.context.get('user').id,
                         self.post.id)

    def check_fields(self, context, obj):
        return self.assertEqual(context, obj)

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse
                                              ('posts:post_detail',
                                               kwargs={'post_id': '1'}))
        self.assertEqual(response.context.get('post').text, 'Тестовая пост')
        self.assertEqual(response.context.get('post').group, self.post.group)
        self.check_fields(response.context.get('post').text, self.post.text)
        self.assertEqual(response.context.get('post').image, self.post.image)

    def test_create_post_page_show_correct_context(self):
        """Шаблон create_post сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_edit_post_page_show_correct_context(self):
        """Шаблон edit_post сформирован с правильным контекстом."""
        Post.objects.create(
            author=self.author,
            text='Тестовая пост',
            id='3'
        )
        response = self.authorized_author.get(reverse
                                              ('posts:post_edit',
                                               kwargs={'post_id': '3'}))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_comment_appears_on_the_page(self):
        self.comment = Comment.objects.create(
            author=self.user,
            post=self.post,
            text='Супер проверочка'
        )
        self.assertTrue(
            Comment.objects.filter(
                author=self.user,
                post=self.post,
                text='Супер проверочка'
            ).exists()
        )

    def test_index_is_cached(self):
        post_cache = Post.objects.create(
            author= self.author,
            text='тестовый пост для проверки кэше'
        )
        response = self.authorized_client.get(reverse('posts:index'))
        post_cache.delete()
        response2 = self.authorized_client.get(reverse('posts:index'))
        self.assertNotEqual(response, response2)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        Post.objects.bulk_create([Post(author=cls.user,
                                       text='Тестовая пост',
                                       group=cls.group) for i in range(13)])

    def setUp(self):
        self.guest_client = Client()

    def test_first_page_index_contains_ten_records(self):
        response = self.client.get(reverse('posts:index'))

        self.assertEqual(len(response.context['page_obj']), 10)

    def test_second_page_index_contains_three_records(self):

        response = self.client.get(reverse('posts:index') + '?page=2')
        self.assertEqual(len(response.context['page_obj']), 3)

    def test_first_page_group_list_contains_ten_records(self):
        response = self.client.get(reverse
                                   ('posts:group_list',
                                    kwargs={'slug': 'test-slug'}))
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_second_page_group_list_contains_three_records(self):
        response = self.client.get(reverse
                                   ('posts:group_list',
                                    kwargs={'slug': 'test-slug'}) + '?page=2')
        self.assertEqual(len(response.context['page_obj']), 3)

    def test_profile_contains_one_records(self):
        response = self.client.get(reverse
                                   ('posts:profile',
                                    kwargs={'username': 'auth'}))
        self.assertEqual(len(response.context['page_obj']), 2)