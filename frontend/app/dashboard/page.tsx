"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { BusinessMe, Customer, Order, Product, TelegramOperator } from "@/lib/types";
import { Card, ErrorMessage, LoadingState } from "@/components/ui";
import { useRouter } from "next/navigation";

export default function OverviewPage() {
  const router = useRouter();
  const [businessState, setBusinessState] = useState<BusinessMe | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [operators, setOperators] = useState<TelegramOperator[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.businessMe(), api.products(), api.orders(), api.customers(), api.operators()])
      .then(([businessMe, productData, orderData, customerData, operatorData]) => {
        if (!businessMe.business || businessMe.membership?.status !== "active") {
          router.replace("/onboarding");
          return;
        }
        setBusinessState(businessMe);
        setProducts(productData);
        setOrders(orderData);
        setCustomers(customerData);
        setOperators(operatorData);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load overview"))
      .finally(() => setLoading(false));
  }, [router]);

  const stats = [
    { label: "Total products", value: products.length },
    { label: "Total orders", value: orders.length },
    { label: "Total customers", value: customers.length },
    { label: "New orders", value: orders.filter((order) => order.status === "new").length },
    { label: "Low stock products", value: products.filter((product) => product.stock_count > 0 && product.stock_count <= 10).length },
    { label: "Out of stock products", value: products.filter((product) => product.stock_count === 0).length }
  ];
  const hasActiveOperator = operators.some((operator) => operator.is_active);

  return (
    <section className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold text-slate-950">
          {businessState?.business ? `Dashboard - ${businessState.business.name}` : "Dashboard"}
        </h1>
        {businessState?.business?.public_business_id && businessState.membership?.role === "owner" && (
          <p className="mt-1 text-sm font-medium text-slate-600">Business ID: {businessState.business.public_business_id}</p>
        )}
        <p className="mt-1 text-sm text-slate-500">Current business totals calculated from products, orders, and customers.</p>
      </div>
      <ErrorMessage message={error} />
      {!loading && !hasActiveOperator && (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          Active operator yo'q. AI operatorga yo'naltira olmaydi.
        </div>
      )}
      {loading ? (
        <LoadingState />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {stats.map((stat) => (
            <Card key={stat.label}>
              <div className="text-sm text-slate-500">{stat.label}</div>
              <div className="mt-2 text-3xl font-semibold text-slate-950">{stat.value}</div>
            </Card>
          ))}
        </div>
      )}
    </section>
  );
}
