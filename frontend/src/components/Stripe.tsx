import { useCallback, useState, useEffect } from "react";
import { loadStripe } from "@stripe/stripe-js";
import {
  EmbeddedCheckoutProvider,
  EmbeddedCheckout,
} from "@stripe/react-stripe-js";
import { Navigate } from "react-router-dom";

import useAuth from "../auth/useAuth";
import { env } from "../utils";

// Make sure to call `loadStripe` outside of a component’s render to avoid
// recreating the `Stripe` object on every render.
// This is your test secret API key.
let pk;
if (env() === "PROD") {
  pk =
    "pk_live_51QzUDlL7uUhJKkiAwv9ZkxpTllA4RszJMPQ75ZnQ2MRhQh89YTfc6MS4YvlauJjWm7cWdAf1SW2ieYGobOsaVOrg00s21nSZm2";
} else {
  pk =
    "pk_test_51QzUDsQ6WPPiKRLM1qcKRe1i6P6ob49uQdFIWHWdFLQcp0BzTDtGL2hKKzyA9tGcED5u2T0MHWQXNjDtdfYj79pe005oNhW9Gx";
}
const stripePromise = loadStripe(pk);

export const StripeCheckout = () => {
  const fetchClientSecret = useCallback(() => {
    // Create a Checkout Session
    return fetch("/api/stripe/create-checkout-session", {
      method: "POST",
      credentials: "include",
      body: JSON.stringify({
        product_id: "gamergate-100-messages",
        quantity: 1,
      }),
    })
      .then((res) => res.json())
      .then((data) => data.clientSecret);
  }, []);

  const options = { fetchClientSecret };

  return (
    <div id="checkout">
      <EmbeddedCheckoutProvider stripe={stripePromise} options={options}>
        <EmbeddedCheckout />
      </EmbeddedCheckoutProvider>
    </div>
  );
};

export const StripeReturn = () => {
  const { user, setUser } = useAuth();
  const [status, setStatus] = useState(null);
  const [customerEmail, setCustomerEmail] = useState("");

  useEffect(() => {
    const queryString = window.location.search;
    const urlParams = new URLSearchParams(queryString);
    const sessionId = urlParams.get("session_id");
    console.log(sessionId);

    fetch(`/api/stripe/session-status?session_id=${sessionId}`, {
      credentials: "include",
    })
      .then((res) => res.json())
      .then((data) => {
        setStatus(data.status);
        setCustomerEmail(data.customer_email);
        if (user) {
          setUser({ ...user, messages_left: data.messages_left });
        }
      });
  }, [user, setUser]);

  if (status === "open") {
    return <Navigate to="/checkout" />;
  }

  if (status === "complete") {
    return (
      <section id="success">
        <p>
          We appreciate your business! A confirmation email will be sent to{" "}
          {customerEmail}. If you have any questions, please email{" "}
          <a href="mailto:narrativedatallc@gmail.com">
            narrativedatallc@gmail.com
          </a>
          .
        </p>
      </section>
    );
  }

  return null;
};
