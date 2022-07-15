from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_page

from .forms import PostForm, CommentForm
from .models import Group, Post, User, Follow


def make_paginator(request, object, pages):
    paginator = Paginator(object, pages)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj


@cache_page(20, key_prefix='index_page')
def index(request):
    posts = Post.objects.all()
    page_obj = make_paginator(request, posts, 10)
    template = 'posts/index.html'
    context = {
        'page_obj': page_obj,
    }
    return render(request, template, context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    template = 'posts/group_list.html'
    posts = group.posts.all()
    page_obj = make_paginator(request, posts, 10)
    context = {
        'group': group,
        'page_obj': page_obj
    }
    return render(request, template, context)


def profile(request, username):
    template = 'posts/profile.html'
    post_author = get_object_or_404(User, username=username)
    posts = post_author.posts.all()
    page_obj = make_paginator(request, posts, 2)
    context = {
        'page_obj': page_obj,
        'post_author': post_author,
    }
    return render(request, template, context)


def post_detail(request, post_id):
    template = 'posts/post_detail.html'
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    comments = post.comments.all()
    context = {
        'post': post,
        'form': form,
        'comments': comments
    }
    return render(request, template, context)


@login_required
def post_create(request):
    template = 'posts/post_create.html'
    form = PostForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('posts:profile', post.author.username)

    context = {
        'form': form
    }
    return render(request, template, context)


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('posts:post_detail', post_id=post_id)

    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if form.is_valid():
        form.save()
        return redirect('posts:post_detail', post_id=post_id)
    context = {
        'post': post,
        'form': form,
        'is_edit': True,
    }
    return render(request, 'posts/post_create.html', context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    """Страница подписок текущего пользователя"""
    user = request.user
    authors = user.follower.values_list('author', flat=True)
    post_list = Post.objects.filter(author__id__in=authors)
    page_obj = make_paginator(request, post_list, 10)
    context = {
        'page_obj': page_obj,
        'user': user,
    }
    return render(request, 'posts/follow_index.html', context)


@login_required
def profile_follow(request, username):
    """Функция подписки на автора."""
    author = User.objects.get(username=username)
    user = request.user
    if user != author and not Follow.objects.filter(author=author,
                                                    user=user).exists():
        Follow.objects.create(author=author, user=user)
    return redirect('posts:profile', username=author)


@login_required
def profile_unfollow(request, username):
    """Функция отмены подписки на автора."""
    author = User.objects.get(username=username)
    user = request.user
    follow_relationship = Follow.objects.get(author=author, user=user)
    follow_relationship.delete()
    return redirect('posts:profile', username=author)
