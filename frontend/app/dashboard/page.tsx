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
      .catch((err) => setError(err instanceof Error ? err.message : "Umumiy ma’lumotlarni yuklab bo‘lmadi"))
      .finally(() => setLoading(false));
  }, [router]);

  const stats = [
    { label: "Jami mahsulotlar", value: products.length },
    { label: "Jami buyurtmalar", value: orders.length },
    { label: "Jami mijozlar", value: customers.length },
    { label: "Yangi buyurtmalar", value: orders.filter((order) => order.status === "new").length },
    { label: "Kam qolgan mahsulotlar", value: products.filter((product) => product.stock_count > 0 && product.stock_count <= 10).length },
    { label: "Qolmagan mahsulotlar", value: products.filter((product) => product.stock_count === 0).length }
  ];
  const hasActiveOperator = operators.some((operator) => operator.is_active);

  return (
    <section className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold text-slate-950">
          {businessState?.business ? `Panel - ${businessState.business.name}` : "Umumiy ko‘rinish"}
        </h1>
        {businessState?.business?.public_business_id && businessState.membership?.role === "owner" && (
          <p className="mt-1 text-sm font-medium text-slate-600">Biznes ID: {businessState.business.public_business_id}</p>
        )}
        <p className="mt-1 text-sm text-slate-500">Mahsulotlar, buyurtmalar va mijozlar bo‘yicha joriy ko‘rsatkichlar.</p>
      </div>
      <ErrorMessage message={error} />
      {!loading && !hasActiveOperator && (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          Aktiv operator yo‘q. AI operatorga yo‘naltira olmaydi.
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
