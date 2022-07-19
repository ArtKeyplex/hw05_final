import shutil
import tempfile

from django import forms
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.conf import settings
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from posts.models import Group, Post, Follow
from posts.forms import PostForm

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
            group=cls.group,
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
        first_object = response.context['page_obj'][0]
        self.assertEqual(first_object.text, self.post.text)
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

    def check_fields(self, obj_list):
        for obj, post_obj in obj_list.items():
            with self.subTest(obj=obj):
                self.assertEqual(obj, post_obj)

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse
                                              ('posts:post_detail',
                                               kwargs={'post_id':
                                                       f'{self.post.id}'}))
        index_object = response.context['post']
        self.object_list = {
            index_object.text: self.post.text,
            index_object.author: self.post.author,
            index_object.pub_date: self.post.pub_date,
            index_object.image: self.post.image

        }
        self.check_fields(self.object_list)

    def test_create_post_page_show_correct_context(self):
        """Шаблон create_post сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form = PostForm()
        expected = (forms.fields.CharField,
                    forms.fields.ImageField,
                    forms.fields.ChoiceField)
        fields = form.fields
        for value in fields:
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_edit_post_page_show_correct_context(self):
        """Шаблон edit_post сформирован с правильным контекстом."""
        test_post = Post.objects.create(
            author=self.author,
            text='Тестовая пост',
            id='3'
        )
        response = self.authorized_author.get(reverse
                                              ('posts:post_edit',
                                               kwargs={'post_id':
                                                       f'{test_post.id}'}))
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
        Post.objects.create(
            author=self.author,
            text=self.post.text)
        Follow.objects.create(user=self.user,
                              author=self.author)
        response = self.authorized_client.get(reverse('posts:follow_index'))
        post_text_0 = response.context['page_obj'][0].text
        self.assertEqual(post_text_0, self.post.text)
        client = User.objects.create(username='Cat')
        self.client = Client()
        self.client.force_login(client)
        response = self.client.get(reverse('posts:follow_index'))
        self.assertEqual(len(response.context['page_obj']), 0)

    def test_index_is_cached(self):
        post_cache = Post.objects.create(
            author=self.author,
            text='тестовый пост для проверки кэше'
        )
        response = self.authorized_client.get(reverse('posts:index'))
        post_cache.delete()
        response2 = self.authorized_client.get(reverse('posts:index'))
        self.assertNotEqual(response, response2)

    def test_authorized_client_can_follow(self):
        new_user = User.objects.create(username='Beton')
        new_authorized_client = Client()
        new_authorized_client.force_login(new_user)
        new_authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.user.username}
            )
        )
        follower = Follow.objects.get(author=self.user, user=new_user)
        self.assertTrue(follower)

    def test_authorized_client_can_unfollow(self):
        new_user = User.objects.create(username='Beton')
        new_authorized_client = Client()
        new_authorized_client.force_login(new_user)
        new_authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.user.username}
            )
        )
        new_authorized_client.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': self.user.username}
            )
        )
        self.assertEqual(Follow.objects.count(), 0)

    def test_follow_index_following(self):
        Follow.objects.create(author=self.user, user=self.author)
        response = self.authorized_author.get(reverse('posts:follow_index'))
        first_object = response.context['page_obj'][0]
        self.assertEqual(first_object.text, self.post.text)


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
