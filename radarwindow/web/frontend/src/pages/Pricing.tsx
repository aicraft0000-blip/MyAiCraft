import { Link } from 'react-router-dom'
import PublicShell from '../components/PublicShell'

const RADAR_CHECKOUT = 'https://buy.stripe.com/YOUR_PAYMENT_LINK_PAYMENT_LINK'
const PRO_CHECKOUT = 'https://buy.stripe.com/YOUR_PAYMENT_LINK_PAYMENT_LINK'

type Tier = {
  name: string
  price: string
  note?: string
  blurb: string
  features: string[]
  highlight?: boolean
  cta: { label: string; href: string; external?: boolean }
}

const TIERS: Tier[] = [
  {
    name: 'Reader',
    price: 'Free',
    blurb: 'Read the public briefs, every week.',
    features: [
      'Full public brief archive',
      'New brief every Monday',
      'No account needed',
    ],
    cta: { label: 'Read the briefs', href: '/p' },
  },
  {
    name: 'Radar',
    price: '£29/mo',
    note: 'founding price',
    blurb: 'Your niche, configured once. The brief arrives; the media kit comes with it.',
    features: [
      'Weekly analyst brief in your niche’s own vocabulary',
      'Full downloadable media kit — platform post drafts, imagery, audio, reel',
      'Daily signal digest',
      'Email delivery',
    ],
    highlight: true,
    cta: { label: 'Subscribe — £29/mo', href: RADAR_CHECKOUT, external: true },
  },
  {
    name: 'Radar Pro',
    price: '£79/mo',
    note: 'founding price',
    blurb: 'Everything in Radar, plus the loop that sharpens every week’s brief.',
    features: [
      'Everything in Radar',
      'Competitor gap tracking',
      'Connected posting via Blotato',
      'Engagement feedback loop — each week’s results tune the next brief',
      'Priority niche tuning',
    ],
    cta: { label: 'Subscribe — £79/mo', href: PRO_CHECKOUT, external: true },
  },
]

export default function Pricing() {
  return (
    <PublicShell>
      <div className="page-title" style={{ textAlign: 'center' }}>
        Pricing
        <p className="page-sub">
          The brief is the product. Posts and media are derivatives — priced accordingly.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: 16, marginTop: 24 }}>
        {TIERS.map(tier => (
          <div key={tier.name} className="card"
            style={{ display: 'flex', flexDirection: 'column', borderColor: tier.highlight ? 'var(--green-border)' : 'var(--border)' }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: tier.highlight ? 'var(--green)' : 'var(--text-h)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              {tier.name}
            </div>
            <div style={{ margin: '10px 0 2px', fontSize: 26, fontWeight: 700, color: 'var(--text-h)' }} className="num">
              {tier.price}
            </div>
            {tier.note && <div style={{ fontSize: 11, color: 'var(--green)' }}>{tier.note}</div>}
            <p style={{ fontSize: 13, color: 'var(--text)', margin: '12px 0', lineHeight: 1.6 }}>{tier.blurb}</p>
            <ul style={{ listStyle: 'none', flex: 1, marginBottom: 16 }}>
              {tier.features.map(f => (
                <li key={f} style={{ fontSize: 13, lineHeight: 1.5, padding: '4px 0', display: 'flex', gap: 8 }}>
                  <span style={{ color: 'var(--green)' }}>·</span>{f}
                </li>
              ))}
            </ul>
            {tier.cta.external ? (
              <a href={tier.cta.href} className={tier.highlight ? 'btn btn-primary' : 'btn btn-ghost'} style={{ justifyContent: 'center' }}>
                {tier.cta.label}
              </a>
            ) : (
              <Link to={tier.cta.href} className="btn btn-ghost" style={{ justifyContent: 'center' }}>
                {tier.cta.label}
              </Link>
            )}
          </div>
        ))}
      </div>

      <p style={{ textAlign: 'center', fontSize: 12, color: 'var(--text-muted)', marginTop: 20 }}>
        Founding prices for early subscribers; locked in for 12 months.
      </p>
    </PublicShell>
  )
}
