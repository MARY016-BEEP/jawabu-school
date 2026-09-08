def allocate_payment(

    payment_amount,

    tuition_balance,

    transport_balance,

    library_balance

):

    allocation = {

        "tuition": 0,

        "transport": 0,

        "library": 0

    }


    # TUITION

    tuition_payment = min(

        payment_amount,

        tuition_balance

    )

    allocation["tuition"] = tuition_payment

    payment_amount -= tuition_payment


    # TRANSPORT

    transport_payment = min(

        payment_amount,

        transport_balance

    )

    allocation["transport"] = transport_payment

    payment_amount -= transport_payment


    # LIBRARY

    library_payment = min(

        payment_amount,

        library_balance

    )

    allocation["library"] = library_payment

    payment_amount -= library_payment


    allocation["remaining_credit"] = (
        payment_amount
    )


    return allocation