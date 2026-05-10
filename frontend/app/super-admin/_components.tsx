"use client";

import Link from "next/link";
import { FormEvent } from "react";
import { Button, EmptyState, Input } from "@/components/ui";

export function PageHeader({ title, description }: { title: string; description: string }) {
  return (
    <div className="mb-4">
      <h1 className="text-2xl font-semibold text-slate-950">{title}</h1>
      <p className="mt-1 text-sm text-slate-500">{description}</p>
    </div>
  );
}

export function SearchBar({
  value,
  placeholder = "Search",
  onChange,
  onSubmit
}: {
  value: string;
  placeholder?: string;
  onChange: (value: string) => void;
  onSubmit: (event: FormEvent) => void;
}) {
  return (
    <form onSubmit={onSubmit} className="mb-4 flex max-w-md gap-2">
      <Input value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} />
      <Button>Search</Button>
    </form>
  );
}

export function AdminTable({ headers, rows }: { headers: string[]; rows: React.ReactNode[][] }) {
  if (!rows.length) return <EmptyState label="No records found." />;
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[860px] text-left text-sm">
        <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
          <tr>{headers.map((header) => <th key={header} className="py-2 pr-3">{header}</th>)}</tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {row.map((cell, cellIndex) => (
                <td key={cellIndex} className="py-3 pr-3 align-top text-slate-700">{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ViewLink({ href }: { href: string }) {
  return (
    <Link href={href} className="inline-flex h-8 items-center rounded-md border border-slate-300 bg-white px-3 text-xs font-medium text-slate-700 hover:bg-slate-50">
      View
    </Link>
  );
}

export function StatusText({ active }: { active: boolean }) {
  return <span className={active ? "text-emerald-700" : "text-red-700"}>{active ? "active" : "inactive"}</span>;
}
