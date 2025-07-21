from rest_framework import serializers

from .models import Category, Tag, Post


class CategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = Category
        fields = ['id', 'name', 'description']


class TagSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tag
        fields = ['id', 'name']


class PostUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ['title', 'content']


class PostSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField()

    # The following field is used to represent the category as a simple string
    # in the serializer. This is to ensure that the category is displayed as a
    # string in the Swagger documentation and can be directly written as a
    # string when creating or updating an object.
    category = serializers.CharField(required=False)

    # The following field is used to represent the tags as a list of strings in
    # the serializer. This is to ensure that the tags are displayed as a list
    # of strings in the Swagger documentation and can be directly written as a
    # list of strings when creating or updating an object.
    tags = serializers.ListField(
        child=serializers.CharField(), required=False
    )

    class Meta:
        model = Post
        fields = [
            'id', 'title', 'content', 'author', 'category',
            'tags', 'created_at', 'updated_at'
        ]

    def create(self, validated_data):
        # Extract tags and category from validated_data
        tags_data = validated_data.pop('tags', [])
        category_data = validated_data.pop('category', None)

        # Create Post instance
        user = self.context['user']
        post = Post.objects.create(author=user, **validated_data)

        # Handle tags
        for tag_data in tags_data:
            tag, created = Tag.objects.get_or_create(name=tag_data)
            post.tags.add(tag)

        # Handle category
        if category_data:
            category, created = Category.objects.get_or_create(
                name=category_data
            )
            post.category = category

        # Save the post instance
        post.save()

        return post

    def update(self, instance, validated_data):
        # Only update title and content fields
        instance.title = validated_data.get('title', instance.title)
        instance.content = validated_data.get('content', instance.content)
        instance.save()
        return instance

    def to_representation(self, instance):
        representation = {
            'id': instance.id,
            'title': instance.title,
            'content': instance.content,
            'author': instance.author.username,
            'category': instance.category.name if instance.category else None,
            'tags': [tag.name for tag in instance.tags.all()],
            'created_at': instance.created_at,
            'updated_at': instance.updated_at,
        }
        return representation
