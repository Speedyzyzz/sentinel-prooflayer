"use client";

import React, { useState } from "react";
import Link from "next/link";
import { ArrowUpRight, ArrowRight, Play, Menu, X, ShieldCheck } from "lucide-react";

export interface NavLink {
  label: string;
  href: string;
  isActive?: boolean;
}

export interface Partner {
  logoUrl: string;
  href: string;
  alt?: string;
}

export interface ResponsiveHeroBannerProps {
  logoUrl?: string;
  backgroundImageUrl?: string;
  navLinks?: NavLink[];
  ctaButtonText?: string;
  ctaButtonHref?: string;
  badgeText?: string;
  badgeLabel?: string;
  title?: string;
  titleLine2?: string;
  description?: string;
  primaryButtonText?: string;
  primaryButtonHref?: string;
  secondaryButtonText?: string;
  secondaryButtonHref?: string;
  partnersTitle?: string;
  partners?: Partner[];
  children?: React.ReactNode;
}

const ResponsiveHeroBanner: React.FC<ResponsiveHeroBannerProps> = ({
  logoUrl = "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=240&q=80",
  backgroundImageUrl = "https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=2000&q=80",
  navLinks = [
    { label: "Command", href: "/", isActive: true },
    { label: "Mandates", href: "/mandates" },
    { label: "Approvals", href: "/approvals" },
    { label: "Evidence DAG", href: "/evidence" },
    { label: "Disputes", href: "/disputes" },
  ],
  ctaButtonText = "Open Studio",
  ctaButtonHref = "/mandates",
  badgeLabel = "ACTIVE",
  badgeText = "Autonomous B2B Mandate & Causal Proof Engine 2026",
  title = "Govern Autonomous Spend",
  titleLine2 = "With Cryptographic Proof",
  description = "Enforce deterministic pre-payment guardrails and compile 18-node causal evidence graphs for instant PayPal dispute defense.",
  primaryButtonText = "Run Judge Scenarios",
  primaryButtonHref = "#scenario-arena",
  secondaryButtonText = "Inspect 3D Core",
  secondaryButtonHref = "#sentinel-core-stage",
  partnersTitle = "Trusted infrastructure standards for autonomous commerce",
  partners = [
    { logoUrl: "https://cdn.simpleicons.org/paypal/ffffff", href: "#scenario-arena", alt: "PayPal" },
    { logoUrl: "https://cdn.simpleicons.org/stripe/ffffff", href: "#scenario-arena", alt: "Stripe" },
    { logoUrl: "https://cdn.simpleicons.org/cloudflare/ffffff", href: "#scenario-arena", alt: "Cloudflare" },
    { logoUrl: "https://cdn.simpleicons.org/anthropic/ffffff", href: "#scenario-arena", alt: "Anthropic" },
    { logoUrl: "https://cdn.simpleicons.org/vercel/ffffff", href: "#scenario-arena", alt: "Vercel" },
  ],
  children,
}) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <section className="w-full isolate min-h-[100dvh] overflow-hidden relative rounded-2xl border border-white/[0.08] bg-[#09090b]">
      <img
        src={backgroundImageUrl}
        alt="Sentinel orbital network background"
        className="w-full h-full object-cover absolute inset-0 opacity-35"
      />
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-[#050507]/85 via-[#050507]/70 to-[#050507] ring-1 ring-black/30" />

      <header className="z-10 xl:top-4 relative">
        <div className="mx-6">
          <div className="flex items-center justify-between pt-4 h-16">
            <Link
              href="/"
              className="inline-flex items-center gap-2.5 px-3 py-1.5 rounded-full bg-white/5 ring-1 ring-white/15 backdrop-blur text-white font-mono text-xs font-bold tracking-wider"
            >
              <ShieldCheck className="w-4 h-4 text-[#10B981]" />
              <span>SENTINEL // PROOFLAYER</span>
              <span className="sr-only" style={{ backgroundImage: `url(${logoUrl})` }} />
            </Link>

            <nav className="hidden md:flex items-center gap-2">
              <div className="flex items-center gap-1 rounded-full bg-white/5 px-1.5 py-1 ring-1 ring-white/10 backdrop-blur">
                {navLinks.map((link, index) => (
                  <Link
                    key={index}
                    href={link.href}
                    className={`px-3 py-1.5 text-sm font-medium hover:text-white font-sans transition-colors ${
                      link.isActive ? "text-white" : "text-white/75"
                    }`}
                  >
                    {link.label}
                  </Link>
                ))}
                <Link
                  href={ctaButtonHref}
                  className="ml-1 inline-flex items-center gap-1.5 rounded-full bg-white px-3.5 py-1.5 text-sm font-medium text-neutral-900 hover:bg-white/90 font-sans transition-transform active:scale-[0.98]"
                >
                  <span>{ctaButtonText}</span>
                  <ArrowUpRight className="h-4 w-4" />
                </Link>
              </div>
            </nav>

            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden inline-flex h-10 w-10 items-center justify-center rounded-full bg-white/10 ring-1 ring-white/15 backdrop-blur"
              aria-expanded={mobileMenuOpen}
              aria-label="Toggle menu"
            >
              {mobileMenuOpen ? (
                <X className="h-5 w-5 text-white/90" />
              ) : (
                <Menu className="h-5 w-5 text-white/90" />
              )}
            </button>
          </div>

          {mobileMenuOpen && (
            <div className="md:hidden mt-3 rounded-2xl bg-[#111317]/95 p-4 ring-1 ring-white/15 backdrop-blur flex flex-col gap-2">
              {navLinks.map((link, index) => (
                <Link
                  key={index}
                  href={link.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className="px-3 py-2 rounded-lg text-sm font-medium text-white/90 hover:bg-white/10"
                >
                  {link.label}
                </Link>
              ))}
              <Link
                href={ctaButtonHref}
                className="mt-1 inline-flex items-center justify-center gap-2 rounded-full bg-white px-4 py-2 text-sm font-medium text-neutral-900"
              >
                <span>{ctaButtonText}</span>
                <ArrowUpRight className="h-4 w-4" />
              </Link>
            </div>
          )}
        </div>
      </header>

      <div className="z-10 relative">
        <div className="pt-14 sm:pt-20 lg:pt-24 max-w-7xl mx-auto px-6 pb-14">
          <div className="mx-auto max-w-3xl text-center">
            <div className="mb-6 inline-flex items-center gap-3 rounded-full bg-white/10 px-2.5 py-1.5 ring-1 ring-white/15 backdrop-blur animate-fade-slide-in-1">
              <span className="inline-flex items-center text-xs font-medium text-neutral-900 bg-[#10B981] rounded-full py-0.5 px-2.5 font-mono font-bold">
                {badgeLabel}
              </span>
              <span className="text-sm font-medium text-white/90 font-sans pr-1">
                {badgeText}
              </span>
            </div>

            <h1 className="sm:text-5xl md:text-6xl leading-[1.08] pb-1 text-4xl text-white tracking-tight font-instrument-serif font-normal animate-fade-slide-in-2">
              {title}
              <br className="hidden sm:block" />
              {titleLine2}
            </h1>

            <p className="sm:text-lg animate-fade-slide-in-3 text-base text-white/80 max-w-2xl mt-5 mx-auto leading-relaxed">
              {description}
            </p>

            <div className="flex flex-col sm:flex-row sm:gap-4 mt-8 gap-3 items-center justify-center animate-fade-slide-in-4">
              <a
                href={primaryButtonHref}
                className="inline-flex items-center gap-2 hover:bg-white/15 text-sm font-medium text-white bg-white/10 ring-white/20 ring-1 rounded-full py-3 px-6 font-sans transition-all active:scale-[0.98]"
              >
                <span>{primaryButtonText}</span>
                <ArrowRight className="h-4 w-4" />
              </a>
              <a
                href={secondaryButtonHref}
                className="inline-flex items-center gap-2 rounded-full bg-white/5 ring-1 ring-white/10 px-6 py-3 text-sm font-medium text-white/90 hover:text-white hover:bg-white/10 font-sans transition-all active:scale-[0.98]"
              >
                <span>{secondaryButtonText}</span>
                <Play className="w-4 h-4 fill-current" />
              </a>
            </div>
          </div>

          {children && <div id="sentinel-core-stage" className="mt-12">{children}</div>}

          <div className="mx-auto mt-16 max-w-5xl border-t border-white/10 pt-8">
            <p className="animate-fade-slide-in-1 text-xs font-mono uppercase tracking-wider text-white/60 text-center">
              {partnersTitle}
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 animate-fade-slide-in-2 text-white/70 mt-6 items-center justify-items-center gap-6">
              {partners.map((partner, index) => (
                <a
                  key={index}
                  href={partner.href}
                  aria-label={partner.alt || `Partner ${index + 1}`}
                  className="inline-flex items-center justify-center bg-center w-[110px] h-[28px] bg-contain bg-no-repeat opacity-70 hover:opacity-100 transition-opacity"
                  style={{ backgroundImage: `url(${partner.logoUrl})` }}
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default ResponsiveHeroBanner;
