!pip install streamlitimport streamlit as st
from mpesa import stk_push
st.subheader("M-Pesa Payment")

if st.button("Send STK Push"):

    try:

        response = stk_push(

            phone_number=parent_phone,

            amount=amount,

            registration_number=registration_number

        )

        checkout_id = response.get(
            "CheckoutRequestID"
        )

        st.success(
            "STK Push sent successfully to parent's phone."
        )

        st.info(
            "Please ask the parent to enter their M-Pesa PIN."
        )

    except Exception as e:

        st.error(str(e))
