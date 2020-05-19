from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

CREATE_USER_URL = reverse('user:create')
TOKEN_URL = reverse('user:token')
ME_URL = reverse('user:me')


def create_user(**params):
    return get_user_model().objects.create_user(**params)


class PublicUserApiTests(TestCase):
    """Test the users API (public)"""

    def setUp(self):
        self.client = APIClient()

    def test_create_valid_user_success(self):
        """Test creating user with valid payload is successful"""

        payload = {
            'email': 'elieish@gmail.com',
            'password': 'testpass',
            'name': 'Test name'
        }

        response = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user = get_user_model().objects.get(**response.data)
        self.assertTrue(user.check_password(payload['password']))
        self.assertNotIn('password', response.data)

    def test_user_exists(self):
        """Test creating user that already exist fails"""

        payload = {
            'email': 'angelina@gmail.com',
            'password': 'testpass',
            'name': 'Angelina Ishimwe'
        }

        create_user(**payload)

        response = self.client.post(CREATE_USER_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_too_short(self):
        """Test that the password must be more than 5 characters"""

        payload = {
            'email': 'angelina@gmail.com',
            'password': 'pw',
            'name': 'Angelina Ishimwe'
        }

        response = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        user_exists = get_user_model().objects.filter(
            email=payload['email']
        ).exists()
        self.assertFalse(user_exists)

    def test_create_token_for_user(self):
        """Test that a token is created for the user"""
        payload = {'email': 'elieish@gmail.com', 'password': 'testpass'}
        create_user(**payload)
        response = self.client.post(TOKEN_URL, payload)

        self.assertIn('token', response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_token_invalid_credentials(self):
        """Test that token is not created if invalid credentials are given"""
        create_user(email='elieish@gmail.com', password='12345')
        payload = {'email': 'elieish@gmail.com', 'password': 'wrong'}
        response = self.client.post(TOKEN_URL, payload)

        self.assertNotIn('token', response.data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_token_no_user(self):
        """Test that token is not created if user does not exist"""
        payload = {'email': 'elieish@gmail.com', 'password': '12345'}
        response = self.client.post(TOKEN_URL, payload)

        self.assertNotIn('token', response.data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_token_missing_field(self):
        """Test that email and password are required"""
        response = self.client.post(
            TOKEN_URL,
            {'email': 'one', 'password': ''}
        )
        self.assertNotIn('token', response.data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_user_unauthorized(self):
        """Test that authentication is required for users"""

        response = self.client.get(ME_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    class PrivateUserApiTests(TestCase):
        """Test API requests that require authentication"""

        def setUp(self):
            self.user = create_user(
                email='elieish@gmail.com',
                password='testpass',
                name='name'
            )

            self.client = APIClient()
            self.client.force_authenticate(user=self.user)

        def test_retrieve_profile_success(self):
            """Test retrieving profile for logged in used"""

            response = self.client.get(ME_URL)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data, {
                'name': self.user.name,
                'email': self.user.email
            })

        def test_post_me_not_allowed(self):
            """Test that POST is not allowed on the me url"""

            response = self.client.post(ME_URL, {})

            self.assertEqual(response.status_code,
                             status.HTTP_405_METHOD_NOT_ALLOWED)

        def test_update_user_profile(self):
            """Test updating the user profile for authenticated user"""

            payload = {'name': 'new name', 'password': 'newpassword123'}

            response = self.client.patch(ME_URL, payload)
            self.user.refresh_from_db()
            self.assertEqual(self.user.name, payload['name'])
            self.assertEqual(self.user.check_password(payload['password']))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
