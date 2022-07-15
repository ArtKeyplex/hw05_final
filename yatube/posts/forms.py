from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Comment, Post


class PostForm(forms.ModelForm):

    class Meta:
        model = Post
        fields = ['text', 'group', 'image']
        widgets = {
            'text': forms.Textarea
        }
        labels = {
            'text': _('Текст'),
            'group': _('Группа'),
        }
        help_texts = {
            'text': 'Текст нового поста',
            'group': 'Группа, к которой будет относиться пост',
        }


class CommentForm(forms.ModelForm):

    class Meta:
        model = Comment
        fields = ['text']
        widgets = {
            'text': forms.Textarea
        }
        labels = {
            'text': _('Текст'),
        }
        help_texts = {
            'text': 'Текст вашего комментария',
        }

