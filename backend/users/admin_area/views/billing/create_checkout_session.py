import stripe  # 👉 stripe sdk for creating customers and checkout sessions
import json  # 👉 included in case payload parsing is needed later

from django.conf import settings  # 👉 accesses environment variables like stripe keys
from django.utils.crypto import get_random_string  # 👉 unused here but could be used for generating tokens
from django.utils import timezone  # 👉 unused here but helpful if tracking timestamps

from rest_framework.decorators import api_view, permission_classes  # 👉 enables function-based views and permission control
from rest_framework.permissions import AllowAny  # 👉 allows public access to this endpoint
from rest_framework.response import Response  # 👉 formats api responses
from rest_framework import status  # 👉 standard http status codes

from core.models import CustomUser  # 👉 custom user model to check for existing accounts
from users.admin_area.models import Plan, PendingSignup, PreCheckoutEmail  # 👉 admin models for plan logic and signup tracking

stripe.api_key = settings.STRIPE_SECRET_KEY  # 👉 sets the secret key to authenticate stripe api calls


@api_view(['POST'])  # 👉 accepts only POST requests
@permission_classes([AllowAny])  # 👉 accessible without authentication
def create_checkout_session(request):
    try:
        data = request.data
        plan_name = data.get('plan_name')
        email = data.get('email')

        # 👉 stores emails for lead tracking or follow-up even before checkout completes
        PreCheckoutEmail.objects.get_or_create(email=email)

        if not plan_name or not email:
            return Response({'error': 'Missing plan or email'}, status=status.HTTP_400_BAD_REQUEST)

        # 🔒 blocks signups from existing users (including canceled/inactive)
        existing_user = CustomUser.objects.filter(email=email).first()
        if existing_user:
            return Response({
                'error': 'This email is already associated with an account. Please log-in.'
            }, status=status.HTTP_403_FORBIDDEN)

        # 🔒 prevents duplicate pending signups
        if PendingSignup.objects.filter(email=email, is_used=False).exists():
            return Response({
                'error': 'A registration link has already been generated for this email. Please complete your registration or wait for it to expire.'
            }, status=status.HTTP_403_FORBIDDEN)

        # 👉 convert trial to monthly for internal plan logic
        actual_plan_name = 'adminMonthly' if plan_name == 'adminTrial' else plan_name

        # 👉 fetch the corresponding plan object
        plan = Plan.objects.get(name=actual_plan_name)

        # 👉 create a stripe customer tied to the user's email
        customer = stripe.Customer.create(email=email)

        # 👉 create the stripe checkout session for subscription
        session = stripe.checkout.Session.create(
            mode='subscription',
            payment_method_types=['card'],
            customer=customer.id,
            line_items=[{
                'price': plan.stripe_price_id,
                'quantity': 1,
            }],
            metadata={
                'plan_name': plan_name  # 👉 store original plan request (adminTrial vs adminMonthly)
            },
            success_url='http://localhost:3000/admin_thank_you?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='http://localhost:3000/admin_plans',
        )

        return Response({'url': session.url}, status=status.HTTP_200_OK)


    except Plan.DoesNotExist:
        return Response({'error': 'Plan not found'}, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        print("❌ Error creating checkout session:", str(e))
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 👉 summary:
# creates a stripe checkout session for an admin plan purchase (trial or paid).
# prevents signups from duplicate or existing users, logs early email leads,
# and returns a stripe-hosted url to complete checkout.
# supports secure, scalable billing logic and prevents abuse of the trial flow.