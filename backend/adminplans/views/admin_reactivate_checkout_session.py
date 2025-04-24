import stripe
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from adminplans.models import AdminPlan

# Stripe API key setup
stripe.api_key = settings.STRIPE_SECRET_KEY

@api_view(['POST'])
@permission_classes([IsAuthenticated])  # 🔐 Only authenticated admins can reactivate
def admin_reactivate_checkout_session(request):
    user = request.user

    # Ensure only admins can access this endpoint
    if user.role != 'admin':
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

    plan_name = request.data.get('plan_name')

    # 🔒 Reactivations cannot use the free trial
    if plan_name == 'adminTrial':
        return Response({'error': 'Free trial is not available for reactivation.'}, status=status.HTTP_400_BAD_REQUEST)

    # Validate that the selected plan exists
    try:
        plan = AdminPlan.objects.get(name=plan_name)
    except AdminPlan.DoesNotExist:
        return Response({'error': 'Selected plan does not exist.'}, status=status.HTTP_404_NOT_FOUND)

    # 🔄 Retrieve or create Stripe customer for this admin
    try:
        customer = stripe.Customer.retrieve(user.admin_profile.admin_stripe_customer_id)
    except Exception:
        customer = stripe.Customer.create(email=user.email)

    # 🧾 Create a Stripe Checkout session for subscription reactivation
    try:
        session = stripe.checkout.Session.create(
            mode='subscription',
            payment_method_types=['card'],
            customer=customer.id,
            line_items=[{
                'price': plan.stripe_price_id,
                'quantity': 1,
            }],
            metadata={
                'reactivated_email': user.email,  # 👈 Used by webhook to detect reactivations
                'plan_name': plan_name,
            },
            success_url='http://localhost:3000/admin_dashboard?reactivated=true',
            cancel_url='http://localhost:3000/admin_settings',
            expand=['subscription']  # 👈 Ensures we get full subscription object in webhook
        )

        # Return session URL to frontend
        return Response({'url': session.url}, status=status.HTTP_200_OK)

    except Exception as e:
        # Stripe error handler
        print(f"❌ Stripe error: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
