import { useCollaboration } from '../../contexts/CollaborationContext'

export default function FooterCards() {
  const data = useCollaboration()
  const cards = data.footerCards

  return (
    <div className="collab-footer">
      {cards.map((c, i) => (
        <article className={`collab-fcard tone-${c.tagClass || 'gray'}`} key={i}>
          <h4>{c.title}</h4>
          <p>{c.desc}</p>
          <span className={`collab-ftag pill-${c.tagClass || 'gray'}`}>{c.tag}</span>
        </article>
      ))}
    </div>
  )
}
